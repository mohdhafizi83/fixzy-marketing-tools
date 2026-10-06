"""F1 database schema: leads, consent ledger, suppression list, campaigns, events."""
import secrets
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _token() -> str:
    return secrets.token_urlsafe(24)


class Lead(db.Model):
    __tablename__ = "leads"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), index=True)              # stored lowercase
    phone = db.Column(db.String(32), index=True)               # normalized MY format: 601XXXXXXXX
    telegram_chat_id = db.Column(db.String(32), index=True)    # registered via bot /start
    source = db.Column(db.String(255))                        # file/crawl/manual
    unsub_token = db.Column(db.String(64), unique=True, default=_token)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def unsubscribe_url(self, channel: str) -> str:
        import config
        return f"{config.PUBLIC_BASE_URL}/unsubscribe/{self.unsub_token}?ch={channel}"


class Consent(db.Model):
    """Consent ledger (Malaysia PDPA 2010).

    Every grant and revocation is recorded and never deleted, so consent
    history can always be proven.
    """
    __tablename__ = "consent"
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), index=True, nullable=False)
    channel = db.Column(db.String(32), nullable=False)        # email / telegram
    granted_at = db.Column(db.DateTime, server_default=db.func.now())
    granted_source = db.Column(db.String(255))                # manual_import_ui, landing_page, etc.
    revoked_at = db.Column(db.DateTime)

    @classmethod
    def active_for(cls, lead_id: int, channel: str) -> bool:
        row = (cls.query.filter_by(lead_id=lead_id, channel=channel)
               .order_by(cls.id.desc()).first())
        return bool(row and row.granted_at and not row.revoked_at)


class Suppression(db.Model):
    """Automatic blocklist: unsubscribed or bounced contacts are never contacted again."""
    __tablename__ = "suppression"
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(32), nullable=False)
    value = db.Column(db.String(255), nullable=False)         # email or normalized phone
    reason = db.Column(db.String(64), nullable=False)         # unsubscribed / bounced / complained
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
    subject = db.Column(db.String(255))                      # email only
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default="draft")       # draft/running/paused/done
    scheduled_at = db.Column(db.DateTime)                   # UTC; when set, APScheduler fires the blast
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Event(db.Model):
    """One record per outbound send — the basis for F2 analytics."""
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), index=True)
    lead_id = db.Column(db.Integer, index=True)
    channel = db.Column(db.String(32))
    status = db.Column(db.String(32))                       # sent / failed / skipped
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class LlmProvider(db.Model):
    """A configurable LLM backend for AI copy drafts (local or cloud).

    Any OpenAI-compatible chat-completions endpoint works: llama.cpp server,
    Ollama, llama-swap (local), or OpenAI / OpenRouter / Groq (cloud).
    base_url is stored WITHOUT the /v1 suffix; the client normalizes it.
    NOTE: api_key lives in the local SQLite DB — treat the DB file as a secret.
    """
    __tablename__ = "llm_providers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)   # "Local (localhost)"
    base_url = db.Column(db.String(255), nullable=False)           # http://host:port
    api_key = db.Column(db.String(255), default="")               # empty for local
    default_model = db.Column(db.String(128), default="")
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Setting(db.Model):
    """Simple key-value app settings editable from the Settings UI.

    DB values override .env values (env acts as the default). Used for
    Search API credentials so the owner can manage them without editing files.
    """
    __tablename__ = "settings"
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(512), default="")
    updated_at = db.Column(db.DateTime, server_default=db.func.now(),
                          onupdate=db.func.now())

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        row = db.session.get(cls, key)
        return row.value if row and row.value else default

    @classmethod
    def set(cls, key: str, value: str):
        row = db.session.get(cls, key)
        if row:
            row.value = value
        else:
            db.session.add(cls(key=key, value=value))
        db.session.commit()


class InboxMessage(db.Model):
    """F3 reply inbox: inbound messages from reply-only channels.

    WhatsApp (and later FB/IG) inbound webhooks land here so the owner can
    read and reply within the 24h window. status: new / replied / archived.
    """
    __tablename__ = "inbox_messages"
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(32), nullable=False, index=True)   # whatsapp / messenger / instagram
    external_id = db.Column(db.String(128), unique=True)            # provider message id (dedup)
    sender_id = db.Column(db.String(128))                           # wa user id / PSID
    sender_name = db.Column(db.String(128))
    text = db.Column(db.Text)
    status = db.Column(db.String(16), default="new")                # new/replied/archived
    received_at = db.Column(db.DateTime, server_default=db.func.now())
