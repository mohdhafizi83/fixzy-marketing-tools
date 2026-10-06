"""Skema DB F1: leads, consent ledger, suppression list, campaigns, events."""
import secrets
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _token() -> str:
    return secrets.token_urlsafe(24)


class Lead(db.Model):
    __tablename__ = "leads"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), index=True)          # sudah lowercase
    phone = db.Column(db.String(32), index=True)          # dinormalisasi MY: 601XXXXXXXX
    telegram_chat_id = db.Column(db.String(32), index=True)  # didaftarkan via /start bot
    source = db.Column(db.String(255))                   # fail/crawl/manual
    unsub_token = db.Column(db.String(64), unique=True, default=_token)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def unsubscribe_url(self, channel: str) -> str:
        import config
        return f"{config.PUBLIC_BASE_URL}/unsubscribe/{self.unsub_token}?ch={channel}"


class Consent(db.Model):
    """Consent ledger (PDPA 2010): setiap grant dan revoke dicatat, tak dipadam."""
    __tablename__ = "consent"
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), index=True, nullable=False)
    channel = db.Column(db.String(32), nullable=False)    # email / telegram
    granted_at = db.Column(db.DateTime, server_default=db.func.now())
    granted_source = db.Column(db.String(255))            # manual_import_ui, landing_page, dsb
    revoked_at = db.Column(db.DateTime)

    @classmethod
    def active_for(cls, lead_id: int, channel: str) -> bool:
        row = (cls.query.filter_by(lead_id=lead_id, channel=channel)
               .order_by(cls.id.desc()).first())
        return bool(row and row.granted_at and not row.revoked_at)


class Suppression(db.Model):
    """Senarai hitam automatik: unsub/bounce → jangan hubungi lagi."""
    __tablename__ = "suppression"
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(32), nullable=False)
    value = db.Column(db.String(255), nullable=False)     # email atau phone dinormalisasi
    reason = db.Column(db.String(64), nullable=False)     # unsubscribed / bounced / complained
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @classmethod
    def is_suppressed(cls, channel: str, value: str) -> bool:
        if not value:
            return False
        return cls.query.filter_by(channel=channel, value=value.lower()).first() is not None


class Campaign(db.Model):
    __tablename__ = "campaigns"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    channel = db.Column(db.String(32), nullable=False)
    subject = db.Column(db.String(255))                  # email sahaja
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default="draft")   # draft/running/paused/done
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Event(db.Model):
    """Satir rekod outbound — asas analytics F2."""
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), index=True)
    lead_id = db.Column(db.Integer, index=True)
    channel = db.Column(db.String(32))
    status = db.Column(db.String(32))                    # sent / failed / skipped
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
