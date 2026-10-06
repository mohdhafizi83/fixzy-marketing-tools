"""Fixzy Marketing Tools — F1 application entry point.

Routes:
  /                     dashboard (lead/campaign counts, channel status)
  /import               import leads: paste text / URL list / crawl a site
  /leads                lead list
  /campaign/new         create a campaign
  /campaign/<id>/start  run a blast (background thread)
  /unsubscribe/<token>  unsubscribe page (PDPA) — GET asks, POST confirms
  /telegram/webhook     bot /start -> register chat_id + consent
"""
import threading
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

import config
from models import db, Lead, Consent, Suppression, Campaign, Event
from extractor import extract_emails, extract_phones_my
from crawler import Crawler

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
db.init_app(app)

with app.app_context():
    db.create_all()


def _get_or_create_lead(email=None, phone=None, source="") -> Lead:
    """Dedup: reuse an existing lead if the lowercase email or normalized phone exists."""
    if email:
        existing = Lead.query.filter_by(email=email.lower()).first()
        if existing:
            return existing
    if phone:
        existing = Lead.query.filter_by(phone=phone).first()
        if existing:
            return existing
    lead = Lead(email=(email or "").lower() or None, phone=phone, source=source)
    db.session.add(lead)
    db.session.flush()
    return lead


@app.route("/")
def dashboard():
    from adapters import get_adapter
    chans = {}
    for ch in ("email", "telegram"):
        a = get_adapter(ch)
        chans[ch] = {"configured": a.is_configured(), "outbound": a.supports_outbound}
    return render_template("dashboard.html",
                         n_leads=Lead.query.count(),
                         n_campaigns=Campaign.query.count(),
                         n_suppressed=Suppression.query.count(),
                         campaigns=Campaign.query.order_by(Campaign.id.desc()).limit(20).all(),
                         channels=chans)


@app.route("/import", methods=["GET", "POST"])
def import_leads():
    if request.method == "GET":
        return render_template("import.html")

    mode = request.form.get("mode")
    text = request.form.get("text", "")
    added = {"email": 0, "phone": 0}

    with app.app_context():
        if mode in ("paste", "file"):
            emails = extract_emails(text)
            phones = extract_phones_my(text)
            for e in emails:
                before = Lead.query.filter_by(email=e.lower()).first()
                lead = _get_or_create_lead(email=e, source=mode)
                if not before:
                    added["email"] += 1
                db.session.add(Consent(lead_id=lead.id, channel="email",
                                     granted_source=f"import_{mode}"))
            for p in phones:
                before = Lead.query.filter_by(phone=p).first()
                lead = _get_or_create_lead(phone=p, source=mode)
                if not before:
                    added["phone"] += 1
        elif mode == "crawl":
            url = text.strip()
            if not url.startswith("http"):
                url = "http://" + url
            c = Crawler(max_pages=int(request.form.get("max_pages", 20)))
            emails, phones = c.crawl_site(url)
            for e in emails:
                before = Lead.query.filter_by(email=e.lower()).first()
                _get_or_create_lead(email=e, source=f"crawl:{url}")
                if not before:
                    added["email"] += 1
            for p in phones:
                before = Lead.query.filter_by(phone=p).first()
                _get_or_create_lead(phone=p, source=f"crawl:{url}")
                if not before:
                    added["phone"] += 1
        db.session.commit()

    flash(f"Import finished: +{added['email']} new emails, +{added['phone']} new phone numbers.")
    return redirect(url_for("leads"))


@app.route("/leads")
def leads():
    return render_template("leads.html", leads=Lead.query.order_by(Lead.id.desc()).limit(500).all(),
                         Consent=Consent)


@app.route("/campaign/new", methods=["GET", "POST"])
def campaign_new():
    if request.method == "POST":
        c = Campaign(name=request.form["name"], channel=request.form["channel"],
                    subject=request.form.get("subject", ""),
                    message=request.form["message"])
        db.session.add(c)
        db.session.commit()
        flash(f"Campaign '{c.name}' created (id {c.id}).")
        return redirect(url_for("dashboard"))
    return render_template("campaign_new.html")


@app.route("/campaign/<int:cid>/start", methods=["POST"])
def campaign_start(cid):
    from scheduler import run_blast
    t = threading.Thread(target=run_blast, args=(app, cid), daemon=True)
    t.start()
    flash(f"Blast for campaign {cid} started (running in background).")
    return redirect(url_for("dashboard"))


@app.route("/unsubscribe/<token>", methods=["GET", "POST"])
def unsubscribe(token):
    lead = Lead.query.filter_by(unsub_token=token).first()
    if not lead:
        return "Token not found.", 404
    channel = request.args.get("ch", "email")
    if request.method == "POST":
        c = Consent.query.filter_by(lead_id=lead.id, channel=channel)\
                        .order_by(Consent.id.desc()).first()
        if c and not c.revoked_at:
            c.revoked_at = db.func.now()
        addr = lead.email if channel == "email" else (lead.phone or lead.telegram_chat_id)
        if addr and not Suppression.is_suppressed(channel, addr):
            db.session.add(Suppression(channel=channel, value=addr.lower(),
                                      reason="unsubscribed"))
        db.session.commit()
        return render_template("unsub_done.html", lead=lead)
    return render_template("unsub_confirm.html", lead=lead, channel=channel)


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    """Telegram update — if the text is /start, register chat_id + telegram consent."""
    data = request.get_json(silent=True) or {}
    msg = data.get("message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()
    if chat_id and text.startswith("/start"):
        with app.app_context():
            lead = Lead.query.filter_by(telegram_chat_id=str(chat_id)).first()
            if not lead:
                lead = Lead(telegram_chat_id=str(chat_id), source="telegram_start")
                db.session.add(lead)
                db.session.flush()
            db.session.add(Consent(lead_id=lead.id, channel="telegram",
                                  granted_source="telegram_start"))
            db.session.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    # Bind 0.0.0.0 so the UI is reachable from the LAN (other phones/desktops).
    # Do NOT expose this directly to the internet — keep it behind a reverse proxy/firewall.
    app.run(host="0.0.0.0", port=5558, debug=False)
