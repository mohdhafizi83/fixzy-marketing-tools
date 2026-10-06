"""PDPA core tests: consent ledger, suppression, eligible_leads gate.

These guard the most safety-critical invariant in the tool: no message may
reach a contact without active consent and without being suppressed.
"""
from datetime import datetime, timezone

from models import db, Lead, Consent, Suppression
from scheduler import eligible_leads


def _mk_lead(email=None, phone=None, chat=None, source="test"):
    lead = Lead(email=email, phone=phone, telegram_chat_id=chat, source=source)
    db.session.add(lead)
    db.session.commit()
    return lead


def _grant(lead_id, channel):
    c = Consent(lead_id=lead_id, channel=channel, granted_source="test")
    db.session.add(c)
    db.session.commit()
    return c


def test_consent_active_after_grant(db_session):
    lead = _mk_lead(email="a@x.com")
    _grant(lead.id, "email")
    assert Consent.active_for(lead.id, "email")


def test_consent_inactive_without_grant(db_session):
    lead = _mk_lead(email="b@x.com")
    assert not Consent.active_for(lead.id, "email")


def test_consent_inactive_after_revoke(db_session):
    lead = _mk_lead(email="c@x.com")
    c = _grant(lead.id, "email")
    c.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()
    assert not Consent.active_for(lead.id, "email")


def test_regrant_after_revoke_is_active(db_session):
    lead = _mk_lead(email="d@x.com")
    c = _grant(lead.id, "email")
    c.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()
    _grant(lead.id, "email")  # newest record wins
    assert Consent.active_for(lead.id, "email")


def test_suppression_blocks_eligibility(db_session, app):
    lead = _mk_lead(email="e@x.com")
    _grant(lead.id, "email")
    camp = _campaign("email")
    assert lead.id in [l.id for l in eligible_leads(app, camp)]
    db.session.add(Suppression(channel="email", value="e@x.com",
                              reason="bounced"))
    db.session.commit()
    assert lead.id not in [l.id for l in eligible_leads(app, camp)]


def test_no_consent_never_eligible(db_session, app):
    lead = _mk_lead(email="f@x.com")  # no consent granted
    camp = _campaign("email")
    assert lead.id not in [l.id for l in eligible_leads(app, camp)]


def test_missing_address_not_eligible(db_session, app):
    lead = _mk_lead(email=None, phone=None)
    _grant(lead.id, "email")
    camp = _campaign("email")
    assert lead.id not in [l.id for l in eligible_leads(app, camp)]


def _campaign(channel):
    from models import Campaign
    c = Campaign(name="t", channel=channel, message="hi", subject="s",
                 status="draft")
    db.session.add(c)
    db.session.commit()
    return c
