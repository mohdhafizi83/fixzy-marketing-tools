"""Webhook signature verification tests (X-Hub-Signature-256, Meta standard).

Meta sends X-Hub-Signature-256: sha256=<hmac_sha256(raw_body, app_secret)>
on webhook POSTs. We verify it when present; a wrong signature must be
rejected with 401 even if the JSON payload looks perfect.
"""
import hashlib
import hmac
import json


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_whatsapp_valid_signature_accepted(app, client):
    from models import Setting
    with app.app_context():
        Setting.set("whatsapp_app_secret", "waSecret")
    body = json.dumps({"entry": []}).encode()
    r = client.post("/webhooks/whatsapp", data=body,
                   content_type="application/json",
                   headers={"X-Hub-Signature-256": _sign("waSecret", body)})
    assert r.status_code == 200


def test_whatsapp_tampered_signature_rejected(app, client):
    from models import Setting
    with app.app_context():
        Setting.set("whatsapp_app_secret", "waSecret")
    body = json.dumps({"entry": []}).encode()
    r = client.post("/webhooks/whatsapp", data=body,
                   content_type="application/json",
                   headers={"X-Hub-Signature-256": _sign("wrong", body)})
    assert r.status_code == 401


def test_meta_messenger_valid_signature_accepted(app, client):
    from models import Setting
    with app.app_context():
        Setting.set("messenger_verify_token", "vTok")
    body = json.dumps({"object": "page", "entry": []}).encode()
    r = client.post("/webhooks/meta", data=body,
                   content_type="application/json",
                   headers={"X-Hub-Signature-256": _sign("vTok", body)})
    assert r.status_code == 200


def test_meta_messenger_tampered_signature_rejected(app, client):
    from models import Setting
    with app.app_context():
        Setting.set("messenger_verify_token", "vTok")
    body = json.dumps({"object": "page", "entry": []}).encode()
    r = client.post("/webhooks/meta", data=body,
                   content_type="application/json",
                   headers={"X-Hub-Signature-256": _sign("evil", body)})
    assert r.status_code == 401
