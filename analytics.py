"""Analytics aggregation for the F2 dashboard.

All numbers come from the events table (one row per outbound send attempt)
plus the suppression list. No fabricated data — if there are no events yet,
the dashboard simply shows zeros.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from models import Campaign, Event, Lead, Suppression, db


def summary():
    """Headline numbers across all campaigns."""
    by_status = dict(
        db.session.query(Event.status, func.count(Event.id))
        .group_by(Event.status).all()
    )
    total = sum(by_status.values())
    sent = by_status.get("sent", 0)
    failed = by_status.get("failed", 0)
    return {
        "total_attempts": total,
        "sent": sent,
        "failed": failed,
        "delivered": by_status.get("delivered", 0),
        "opened": by_status.get("opened", 0),
        "bounced": by_status.get("bounced", 0),
        "success_rate": (sent / total * 100) if total else 0.0,
        "leads": Lead.query.count(),
        "suppressed": Suppression.query.count(),
    }


def per_channel(days: int = 30):
    """Per-channel sent/failed counts for the last N days."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    rows = (
        db.session.query(Event.channel, Event.status, func.count(Event.id))
        .filter(Event.created_at >= since)
        .group_by(Event.channel, Event.status)
        .all()
    )
    out = defaultdict(lambda: {"sent": 0, "failed": 0, "delivered": 0,
                              "opened": 0, "bounced": 0})
    for channel, status, n in rows:
        if status in ("sent", "failed", "delivered", "opened", "bounced"):
            out[channel][status] = n
    return dict(out)


def per_campaign(limit: int = 20):
    """Per-campaign breakdown with success rate."""
    campaigns = Campaign.query.order_by(Campaign.id.desc()).limit(limit).all()
    out = []
    for c in campaigns:
        rows = dict(
            db.session.query(Event.status, func.count(Event.id))
            .filter(Event.campaign_id == c.id).group_by(Event.status).all()
        )
        sent = rows.get("sent", 0)
        failed = rows.get("failed", 0)
        total = sent + failed
        out.append({
            "id": c.id, "name": c.name, "channel": c.channel, "status": c.status,
            "sent": sent, "failed": failed,
            "success_rate": (sent / total * 100) if total else 0.0,
            "scheduled_at": c.scheduled_at,
        })
    return out


def suppression_breakdown():
    """Why contacts are suppressed (unsubscribed / bounced / complained)."""
    rows = (
        db.session.query(Suppression.channel, Suppression.reason, func.count(Suppression.id))
        .group_by(Suppression.channel, Suppression.reason).all()
    )
    return [{"channel": ch, "reason": r, "count": n} for ch, r, n in rows]


def recent_failures(limit: int = 10):
    """Most recent failed sends with their error detail — for debugging."""
    evs = (Event.query.filter_by(status="failed")
           .order_by(Event.id.desc()).limit(limit).all())
    return [{"id": e.id, "channel": e.channel, "lead_id": e.lead_id,
             "detail": e.detail, "at": e.created_at} for e in evs]
