"""Blast scheduler — rate-limited campaign sending (brief section 5).

A blast sends a campaign message to every eligible lead:
  - has ACTIVE consent for that channel (PDPA)
  - is NOT on the suppression list
  - has an address for that channel

Rate limit: a configurable maximum per hour; sends pause at the cap and
resume when the next hourly window opens.
"""
import time
from datetime import datetime, timezone

from models import db, Lead, Consent, Suppression, Campaign, Event


def eligible_leads(app, campaign: Campaign) -> list[Lead]:
    with app.app_context():
        out = []
        for lead in Lead.query.all():
            if not Consent.active_for(lead.id, campaign.channel):
                continue
            addr = lead.email if campaign.channel == "email" else \
                (lead.telegram_chat_id if campaign.channel == "telegram" else
                 (lead.phone if campaign.channel == "sms" else None))
            if not addr or Suppression.is_suppressed(campaign.channel, addr):
                continue
            out.append(lead)
        return out


def run_blast(app, campaign_id: int):
    """Send one blast, respecting the per-channel rate limit.

    Called from the UI (background thread) or from APScheduler.
    """
    import config
    from adapters import get_adapter

    with app.app_context():
        campaign = db.session.get(Campaign, campaign_id)
        if not campaign or campaign.status not in ("draft", "running"):
            return
        campaign.status = "running"
        db.session.commit()

        adapter = get_adapter(campaign.channel)
        cap = config.RATE_LIMITS_PER_HOUR.get(campaign.channel, 100)
        window_start = datetime.now(timezone.utc)
        sent_in_window = 0

        for lead in eligible_leads(app, campaign):
            if sent_in_window >= cap:
                # Wait until the next hourly window opens
                sleep_s = 3600 - (datetime.now(timezone.utc) - window_start).total_seconds()
                if sleep_s > 0:
                    time.sleep(sleep_s)
                window_start = datetime.now(timezone.utc)
                sent_in_window = 0

            result = adapter.send(lead, campaign.message, campaign.subject)
            ev = Event(campaign_id=campaign.id, lead_id=lead.id,
                      channel=campaign.channel,
                      status="sent" if result.ok else "failed",
                      detail=result.detail)
            db.session.add(ev)
            db.session.commit()
            sent_in_window += 1

        campaign.status = "done"
        db.session.commit()
