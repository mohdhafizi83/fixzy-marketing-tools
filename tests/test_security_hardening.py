"""Security hardening tests: CSRF, security headers, SSRF guard, auth timing.

Covers the controls added in the security review:
  - CSRF token required on every state-changing non-webhook request
  - Security headers present on every response
  - Crawler refuses private/internal targets (SSRF)
  - Admin auth uses constant-time comparison (behavioral: wrong creds 401)
  - Telegram webhook fails closed when its secret is configured
"""


def _csrf(client):
    """GET any page to seed a session, then pull the token from the cookie jar."""
    raw = getattr(client, "client", client)  # unwrap _AuthClient if needed
    raw.get("/", auth=("admin", "test-admin-pw"))
    with raw.session_transaction() as sess:
        return sess.get("csrf_token")


# --- CSRF -------------------------------------------------------------------

def test_post_without_csrf_rejected(auth_client):
    r = auth_client.post("/campaign/new",
                       data={"name": "x", "channel": "email", "message": "hi"})
    assert r.status_code == 400


def test_post_with_csrf_accepted(auth_client):
    tok = _csrf(auth_client)
    r = auth_client.post("/campaign/new",
                        data={"name": "ok", "channel": "email",
                            "message": "hi", "csrf_token": tok})
    assert r.status_code == 302  # created + redirect


def test_webhooks_exempt_from_csrf(app, client):
    """Provider webhooks cannot hold our session; they use their own secrets."""
    from models import Setting
    with app.app_context():
        Setting.set("brevo_webhook_secret", "whk")
    r = client.post("/webhooks/brevo?key=whk",
                   json={"event": "delivered", "email": "a@b.co"})
    assert r.status_code == 200


# --- Security headers ---------------------------------------------------------

def test_security_headers_present(auth_client):
    r = auth_client.get("/")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["Referrer-Policy"] == "same-origin"


# --- SSRF guard ---------------------------------------------------------------

def test_crawler_blocks_metadata_ip():
    from crawler import check_target_allowed
    ok, _ = check_target_allowed("http://169.254.169.254/latest/meta-data/")
    assert not ok


def test_crawler_blocks_loopback_and_lan():
    from crawler import check_target_allowed
    for url in ("http://127.0.0.1:8080/admin",
               "http://192.168.0.7/internal",
               "http://10.0.0.1/x",
               "http://[::1]/x"):
        ok, _ = check_target_allowed(url)
        assert not ok, url


def test_crawler_blocks_non_http_scheme():
    from crawler import check_target_allowed
    ok, _ = check_target_allowed("file:///etc/passwd")
    assert not ok


def test_import_crawl_mode_refuses_private_target(auth_client):
    tok = _csrf(auth_client)
    r = auth_client.post("/import", data={
        "mode": "crawl", "text": "http://169.254.169.254/",
        "csrf_token": tok})
    assert r.status_code == 302
    # The flash message should mention the refusal, not a crash
    raw = getattr(auth_client, "client", auth_client)
    with raw.session_transaction() as sess:
        msgs = sess.get("_flashes", [])
    assert any("refused" in (m[1] if isinstance(m, tuple) else str(m)).lower()
              for m in msgs)


# --- Admin auth ---------------------------------------------------------------

def test_wrong_password_rejected(client):
    r = client.get("/", auth=("admin", "wrong-password"))
    assert r.status_code == 401


def test_correct_password_accepted(client):
    r = client.get("/", auth=("admin", "test-admin-pw"))
    assert r.status_code == 200


# --- Telegram webhook secret ----------------------------------------------------

def test_telegram_webhook_fails_closed_when_secret_set(app, client):
    from models import Setting
    with app.app_context():
        Setting.set("telegram_webhook_secret", "tgSecret")
    r = client.post("/telegram/webhook", json={
        "message": {"chat": {"id": 1}, "text": "/start"}})
    assert r.status_code == 403


def test_telegram_webhook_accepts_matching_secret(app, client):
    from models import Setting
    with app.app_context():
        Setting.set("telegram_webhook_secret", "tgSecret")
    r = client.post("/telegram/webhook",
                    json={"message": {"chat": {"id": 99}, "text": "/start"}},
                    headers={"X-Telegram-Bot-Api-Secret-Token": "tgSecret"})
    assert r.status_code == 200
    from models import Lead
    with app.app_context():
        assert Lead.query.filter_by(telegram_chat_id="99").first() is not None
