"""Second hardening pass: headers detail, body cap, error hygiene, rate
limiting, SSRF on user-configured outbound URLs (LLM / SearXNG), and the
SECRET_KEY fail-closed policy.
"""


def _csrf(client):
    raw = getattr(client, "client", client)
    raw.get("/", auth=("admin", "test-admin-pw"))
    with raw.session_transaction() as sess:
        return sess.get("csrf_token")


# --- Headers -----------------------------------------------------------------

def test_csp_default_src_none_and_lockdowns(auth_client):
    csp = auth_client.get("/").headers["Content-Security-Policy"]
    assert csp.startswith("default-src 'none'")
    for directive in ("frame-ancestors 'none'", "base-uri 'none'",
                      "form-action 'self'", "object-src 'none'"):
        assert directive in csp
    # honest scoping: inline script/style are the only 'unsafe-inline' users
    assert "script-src 'self' 'unsafe-inline'" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp
    assert csp.count("unsafe-inline") == 2


def test_xss_protection_disabled_and_permissions_policy(auth_client):
    r = auth_client.get("/")
    assert r.headers["X-XSS-Protection"] == "0"
    assert "camera=()" in r.headers["Permissions-Policy"]


def test_cache_control_no_store_on_settings_and_api(auth_client):
    assert auth_client.get("/settings/llm").headers["Cache-Control"] == "no-store"
    r = auth_client.post("/campaign/draft", json={})
    assert r.headers["Cache-Control"] == "no-store"


# --- Body cap ------------------------------------------------------------------

def test_oversize_body_rejected_413(auth_client):
    tok = _csrf(auth_client)
    big = "x" * (2 * 1024 * 1024)  # > 1 MB MAX_CONTENT_LENGTH
    r = auth_client.post("/import",
                         data={"mode": "paste", "text": big,
                               "csrf_token": tok})
    assert r.status_code == 413
    assert "too large" in r.get_data(as_text=True).lower()


# --- Error hygiene ---------------------------------------------------------------

def test_internal_error_never_leaks_traceback(client):
    r = client.get("/_boom_test", auth=("admin", "test-admin-pw"))
    assert r.status_code == 500
    body = r.get_data(as_text=True)
    assert "secret internal detail" not in body
    assert "Traceback" not in body


# --- Rate limiting ---------------------------------------------------------------

def test_webhook_rate_limited(client, app):
    import ratelimit
    from models import Setting
    ratelimit.reset()
    with app.app_context():
        Setting.set("brevo_webhook_secret", "rl")
    # burst past the webhook window limit
    codes = set()
    for _ in range(70):
        r = client.post("/webhooks/brevo?key=rl",
                        json={"event": "delivered", "email": "a@b.co"})
        codes.add(r.status_code)
        if 429 in codes:
            break
    assert 429 in codes
    ratelimit.reset()


def test_failed_logins_rate_limited_but_success_always_ok(client):
    import ratelimit
    ratelimit.reset()
    codes = {client.get("/", auth=("admin", "wrong")).status_code
             for _ in range(15)}
    assert 429 in codes  # brute force throttled
    # a correct login is never blocked, even after failures
    assert client.get("/", auth=("admin", "test-admin-pw")).status_code == 200
    ratelimit.reset()


# --- SSRF on user-configured outbound URLs ------------------------------------------

class _FakeProvider:
    def __init__(self, base_url):
        self.base_url = base_url
        self.api_key = ""
        self.default_model = ""


def test_netguard_blocks_metadata_loopback_and_userinfo():
    from netguard import check_url_allowed
    for url in ("http://169.254.169.254/latest/meta-data/",
                "http://127.0.0.1:11434/v1",
                "http://10.0.0.5/v1",
                "file:///etc/passwd",
                "http://user:***@example.com/v1"):
        ok, _ = check_url_allowed(url)
        assert not ok, url


def test_netguard_allows_public_https():
    from netguard import check_url_allowed
    ok, reason = check_url_allowed("https://api.openai.com/v1")
    assert ok, reason


def test_llm_provider_private_url_blocked_by_default():
    import aicopy
    err = aicopy.check_provider(_FakeProvider("http://169.254.169.254/v1"))
    assert "private" in err.lower() or "blocked" in err.lower()


def test_llm_provider_loopback_allowed_with_escape_hatch(monkeypatch):
    import aicopy
    import config
    monkeypatch.setattr(config, "ALLOW_PRIVATE_LLM", True)
    assert aicopy.check_provider(
        _FakeProvider("http://localhost:11434")) == ""


def test_llm_draft_refuses_private_provider_without_network(auth_client):
    """A provider pointing at the metadata IP must fail with 400 + refusal,
    never make the request."""
    from models import LlmProvider, db
    with auth_client.client.application.app_context():
        p = LlmProvider(name="evil", base_url="http://169.254.169.254",
                        api_key="", default_model="m", is_default=False)
        db.session.add(p)
        db.session.commit()
        pid = p.id
    tok = _csrf(auth_client)
    r = auth_client.post("/campaign/draft",
                         json={"brief": "hi", "provider_id": pid,
                               "model": "m", "csrf_token": tok},
                         headers={"X-CSRF-Token": tok})
    assert r.status_code == 400
    assert "private" in r.json["error"].lower() or "blocked" in r.json["error"].lower()
    with auth_client.client.application.app_context():
        db.session.delete(db.session.get(LlmProvider, pid))
        db.session.commit()


def test_llm_provider_add_rejects_private_url(auth_client):
    tok = _csrf(auth_client)
    r = auth_client.post("/settings/llm", data={
        "action": "add", "name": "evil", "api_key": "",
        "default_model": "", "base_url": "http://169.254.169.254",
        "csrf_token": tok})
    assert r.status_code == 302
    raw = getattr(auth_client, "client", auth_client)
    with raw.session_transaction() as sess:
        msgs = sess.get("_flashes", [])
    assert any("not saved" in (m[1] if isinstance(m, tuple) else str(m)).lower()
               for m in msgs)
    from models import LlmProvider
    with raw.application.app_context():
        assert LlmProvider.query.filter_by(name="evil").first() is None


def test_searxng_save_rejects_private_url(auth_client):
    tok = _csrf(auth_client)
    r = auth_client.post("/settings/search", data={
        "action": "save", "serpapi_key": "",
        "searxng_url": "http://192.168.1.5:8080", "csrf_token": tok})
    assert r.status_code == 302
    from models import Setting
    with auth_client.client.application.app_context():
        assert Setting.get("searxng_url") in ("", None)


def test_searxng_private_url_blocked_without_network(app):
    import searchapi
    from models import Setting
    with app.app_context():
        Setting.set("serpapi_key", "")
        Setting.set("searxng_url", "http://169.254.169.254")
        urls, err = searchapi._searxng("q", 5)
    assert urls == []
    assert "blocked" in err.lower()
    with app.app_context():
        Setting.set("searxng_url", "")


# --- SECRET_KEY policy -----------------------------------------------------------

def test_secret_key_generated_when_unset(monkeypatch):
    """No hardcoded fallback: with SECRET_KEY unset/empty, config generates a
    strong ephemeral key at startup and logs a warning (fail-closed policy)."""
    import contextlib
    import importlib
    import io

    import config
    monkeypatch.setenv("SECRET_KEY", "")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fresh = importlib.reload(config)
    assert len(fresh.SECRET_KEY) >= 32
    assert "WARNING" in buf.getvalue()
    importlib.reload(config)  # restore real values for later tests


def test_max_content_length_is_1mb(app):
    assert app.config["MAX_CONTENT_LENGTH"] == 1024 * 1024
