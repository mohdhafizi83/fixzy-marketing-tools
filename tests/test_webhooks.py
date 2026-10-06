"""Webhook security + PDPA wiring tests (Brevo events, Meta handshake)."""

BREVO_URL = "/webhooks/brevo"


def _set_secret(app, value):
    from models import Setting
    with app.app_context():
        Setting.set("brevo_webhook_secret", value)


def test_brevo_fail_closed_when_secret_unset(app, client):
    _set_secret(app, "")
    r = client.post(BREVO_URL, json={"event": "delivered", "email": "a@x.com"})
    assert r.status_code == 403


def test_brevo_wrong_key_rejected(app, client):
    _set_secret(app, "s3cret")
    r = client.post(BREVO_URL + "?key=nope",
                   json={"event": "delivered", "email": "a@x.com"})
    assert r.status_code == 403


def test_brevo_hard_bounce_suppresses(app, client):
    _set_secret(app, "s3cret")
    r = client.post(BREVO_URL + "?key=s3cret",
                   json={"event": "hard_bounce", "email": "ghost@x.com",
                        "reason": "user unknown"})
    assert r.status_code == 200
    from models import Suppression
    with app.app_context():
        assert Suppression.is_suppressed("email", "ghost@x.com")


def test_brevo_spam_suppresses_as_complained(app, client):
    _set_secret(app, "s3cret")
    client.post(BREVO_URL + "?key=s3cret",
               json={"event": "spam", "email": "grumpy@x.com"})
    from models import Suppression
    with app.app_context():
        s = Suppression.query.filter_by(value="grumpy@x.com").first()
        assert s and s.reason == "complained"


def test_brevo_unsubscribe_revokes_consent(app, client):
    _set_secret(app, "s3cret")
    from models import db, Lead, Consent
    with app.app_context():
        lead = Lead(email="unsub@x.com", source="test")
        db.session.add(lead)
        db.session.commit()
        c = Consent(lead_id=lead.id, channel="email", granted_source="test")
        db.session.add(c)
        db.session.commit()
        assert Consent.active_for(lead.id, "email")
    client.post(BREVO_URL + "?key=s3cret",
               json={"event": "unsubscribed", "email": "unsub@x.com"})
    with app.app_context():
        assert not Consent.active_for(lead.id, "email")
        from models import Suppression
        assert Suppression.is_suppressed("email", "unsub@x.com")


def test_brevo_opened_records_event(app, client):
    _set_secret(app, "s3cret")
    client.post(BREVO_URL + "?key=s3cret",
               json={"event": "unique_opened", "email": "opener@x.com"})
    from models import Event
    with app.app_context():
        ev = Event.query.filter_by(status="opened", channel="email").first()
        assert ev is not None


def test_brevo_unknown_event_400(app, client):
    _set_secret(app, "s3cret")
    r = client.post(BREVO_URL + "?key=s3cret",
                   json={"event": "teleported", "email": "x@y.zz"})
    assert r.status_code == 400


def test_meta_webhook_fail_closed(app, client):
    from models import Setting
    with app.app_context():
        Setting.set("messenger_verify_token", "")
    r = client.get("/webhooks/meta?hub.mode=subscribe"
                   "&hub.verify_token=&hub.challenge=1")
    assert r.status_code == 403


def test_meta_webhook_handshake_and_inbound(app, client):
    from models import Setting
    with app.app_context():
        Setting.set("messenger_verify_token", "vTok")
    r = client.get("/webhooks/meta?hub.mode=subscribe"
                  "&hub.verify_token=vTok&hub.challenge=42")
    assert r.status_code == 200 and r.data == b"42"
    # inbound messenger message
    r = client.post("/webhooks/meta", json={
        "object": "page",
        "entry": [{"messaging": [
            {"sender": {"id": "PSID1"},
             "message": {"mid": "m.1", "text": "hello"}}]}]})
    assert r.status_code == 200
    from models import InboxMessage
    with app.app_context():
        m = InboxMessage.query.filter_by(external_id="m.1").first()
        assert m and m.channel == "messenger"
        # duplicate is deduped
        client.post("/webhooks/meta", json={
            "object": "page",
            "entry": [{"messaging": [
                {"sender": {"id": "PSID1"},
                 "message": {"mid": "m.1", "text": "dup"}}]}]})
        assert InboxMessage.query.filter_by(external_id="m.1").count() == 1
