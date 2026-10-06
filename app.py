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
from datetime import datetime, timezone
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

# --- APScheduler: fire blasts whose scheduled_at has arrived -------------------
from apscheduler.schedulers.background import BackgroundScheduler
from scheduler import run_blast

scheduler = BackgroundScheduler(timezone="UTC")


def _schedule_existing_campaigns():
    """On startup, re-arm all pending scheduled blasts (survives restarts)."""
    with app.app_context():
        pending = (Campaign.query
                   .filter(Campaign.status == "draft",
                           Campaign.scheduled_at.isnot(None),
                           Campaign.scheduled_at > datetime.now(timezone.utc).replace(tzinfo=None))
                   .all())
        for c in pending:
            scheduler.add_job(run_blast_job, "date", run_date=c.scheduled_at,
                             args=[c.id], id=f"blast_{c.id}", replace_existing=True)
        return len(pending)


def run_blast_job(campaign_id: int):
    """APScheduler entry point (module-level so it survives serialization)."""
    run_blast(app, campaign_id)


scheduler.start()
with app.app_context():
    n = _schedule_existing_campaigns()
    if n:
        print(f"Scheduler armed {n} pending scheduled blast(s).")


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
    for ch in ("email", "telegram", "sms"):
        a = get_adapter(ch)
        chans[ch] = {"configured": a.is_configured(), "outbound": a.supports_outbound}
    return render_template("dashboard.html",
                         n_leads=Lead.query.count(),
                         n_campaigns=Campaign.query.count(),
                         n_suppressed=Suppression.query.count(),
                         campaigns=Campaign.query.order_by(Campaign.id.desc()).limit(20).all(),
                         channels=chans)


@app.route("/analytics")
def analytics():
    """F2 analytics dashboard — real numbers from the events table."""
    import analytics as an
    return render_template("analytics.html",
                         summary=an.summary(),
                         per_channel=an.per_channel(),
                         per_campaign=an.per_campaign(),
                         suppression=an.suppression_breakdown(),
                         failures=an.recent_failures())


@app.route("/import", methods=["GET", "POST"])
def import_leads():
    if request.method == "GET":
        import searchapi
        return render_template("import.html", search_backend=searchapi.active_backend())

    mode = request.form.get("mode")
    text = request.form.get("text", "")
    added = {"email": 0, "phone": 0}

    # Optional uploaded file (.txt/.csv): its content is treated like pasted text
    upload = request.files.get("file")
    if upload and upload.filename:
        try:
            text = upload.read().decode("utf-8", errors="ignore")
        except Exception:
            flash("Could not read the uploaded file.")
            return redirect(url_for("import_leads"))
        mode = "file"

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
        elif mode == "search":
            # F2: discover source URLs via search API, crawl each for contacts
            from searchapi import search
            urls, err = search(text.strip(), num=5)
            if not urls:
                flash(f"Search failed: {err}")
                return redirect(url_for("import_leads"))
            c = Crawler(max_pages=int(request.form.get("max_pages", 5)))
            for u in urls:
                e_list, p_list = c.crawl_site(u)
                for e in e_list:
                    before = Lead.query.filter_by(email=e.lower()).first()
                    _get_or_create_lead(email=e, source=f"search:{u}")
                    if not before:
                        added["email"] += 1
                for p in p_list:
                    before = Lead.query.filter_by(phone=p).first()
                    _get_or_create_lead(phone=p, source=f"search:{u}")
                    if not before:
                        added["phone"] += 1
        db.session.commit()

    flash(f"Import finished: +{added['email']} new emails, +{added['phone']} new phone numbers.")
    return redirect(url_for("leads"))


@app.route("/leads")
def leads():
    return render_template("leads.html", leads=Lead.query.order_by(Lead.id.desc()).limit(500).all(),
                         Consent=Consent)


@app.route("/export")
def export_leads():
    """Export all leads to CSV or TXT (legacy feature: TXT/CSV export).

    CSV columns: email, phone, telegram_chat_id, source, created_at
    TXT: one email per line (matches the legacy output format).
    """
    import csv, io
    from flask import Response

    fmt = request.args.get("fmt", "csv")
    leads = Lead.query.order_by(Lead.id).all()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")

    if fmt == "txt":
        buf = "\n".join(l.email for l in leads if l.email)
        return Response(buf + "\n", mimetype="text/plain",
                      headers={"Content-Disposition":
                              f"attachment; filename=leads_{ts}.txt"})

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["email", "phone", "telegram_chat_id", "source", "created_at"])
    for l in leads:
        w.writerow([l.email or "", l.phone or "", l.telegram_chat_id or "",
                    l.source or "", l.created_at or ""])
    return Response(out.getvalue(), mimetype="text/csv",
                   headers={"Content-Disposition":
                           f"attachment; filename=leads_{ts}.csv"})


@app.route("/campaign/draft", methods=["POST"])
def campaign_draft():
    """AI copy draft endpoint. Optional provider_id + model in the JSON body."""
    from aicopy import draft_message
    from models import LlmProvider
    body = request.json or {}
    brief = body.get("brief", "").strip()
    channel = body.get("channel", "email")
    provider = None
    if body.get("provider_id"):
        provider = db.session.get(LlmProvider, body["provider_id"])
        if not provider:
            return jsonify({"ok": False, "error": "Provider not found"}), 404
    draft, err = draft_message(brief, channel, provider=provider,
                              model=body.get("model") or None)
    if draft is None:
        return jsonify({"ok": False, "error": err}), 502
    return jsonify({"ok": True, "draft": draft})


@app.route("/settings/llm", methods=["GET", "POST"])
def settings_llm():
    """Manage LLM providers (local or cloud, OpenAI-compatible)."""
    from models import LlmProvider
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name = request.form.get("name", "").strip()
            base_url = request.form.get("base_url", "").strip()
            if not name or not base_url:
                flash("Name and base URL are required.")
                return redirect(url_for("settings_llm"))
            p = LlmProvider(name=name, base_url=base_url,
                           api_key=request.form.get("api_key", "").strip(),
                           default_model=request.form.get("default_model", "").strip(),
                           is_default=not LlmProvider.query.first())
            db.session.add(p)
            db.session.commit()
            flash(f"Provider '{name}' added.")
        elif action == "set_default":
            pid = int(request.form.get("id", 0))
            for p in LlmProvider.query.all():
                p.is_default = (p.id == pid)
            db.session.commit()
            flash("Default provider updated.")
        elif action == "delete":
            pid = int(request.form.get("id", 0))
            p = db.session.get(LlmProvider, pid)
            if p:
                db.session.delete(p)
                db.session.commit()
                flash(f"Provider '{p.name}' deleted.")
        return redirect(url_for("settings_llm"))

    providers = LlmProvider.query.order_by(LlmProvider.id).all()
    # Try to list each provider's models for display
    from aicopy import list_models
    info = []
    for p in providers:
        models, err = list_models(p)
        info.append({"p": p, "models": models, "err": err})
    # Search API settings (DB overrides .env)
    from models import Setting
    import searchapi
    search_cfg = {
        "serpapi_key": Setting.get("serpapi_key") or config.SERPAPI_KEY,
        "searxng_url": Setting.get("searxng_url") or config.SEARXNG_URL,
        "backend": searchapi.active_backend(),
    }
    return render_template("settings_llm.html", info=info, search=search_cfg)


@app.route("/settings/search", methods=["POST"])
def settings_search():
    """Save Search API credentials (SerpAPI key / SearXNG URL) from the UI."""
    from models import Setting
    action = request.form.get("action")
    if action == "save":
        Setting.set("serpapi_key", request.form.get("serpapi_key", "").strip())
        Setting.set("searxng_url", request.form.get("searxng_url", "").strip())
        flash("Search API settings saved.")
    elif action == "test":
        import searchapi
        urls, err = searchapi.search("test query malaysia", num=3)
        if urls:
            flash(f"Search API works — backend '{searchapi.active_backend()}' "
                  f"returned {len(urls)} URLs. First: {urls[0]}")
        else:
            flash(f"Search test FAILED: {err}")
    return redirect(url_for("settings_llm"))


@app.route("/settings/llm/models", methods=["POST"])
def settings_llm_models():
    """Return a provider's model list as JSON (for the campaign form dropdown)."""
    from models import LlmProvider
    from aicopy import list_models
    pid = int((request.json or {}).get("provider_id", 0))
    p = db.session.get(LlmProvider, pid)
    if not p:
        return jsonify({"ok": False, "error": "Provider not found"}), 404
    models, err = list_models(p)
    return jsonify({"ok": bool(models), "models": models, "error": err})


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
    from models import LlmProvider
    return render_template("campaign_new.html", providers=LlmProvider.query.order_by(LlmProvider.id).all())


@app.route("/campaign/<int:cid>/start", methods=["POST"])
def campaign_start(cid):
    from scheduler import run_blast
    t = threading.Thread(target=run_blast, args=(app, cid), daemon=True)
    t.start()
    flash(f"Blast for campaign {cid} started (running in background).")
    return redirect(url_for("dashboard"))


@app.route("/campaign/<int:cid>/schedule", methods=["POST"])
def campaign_schedule(cid):
    """Schedule a draft campaign to blast at a specific UTC time."""
    c = db.session.get(Campaign, cid)
    if not c or c.status != "draft":
        flash("Only draft campaigns can be scheduled.")
        return redirect(url_for("dashboard"))
    when_str = request.form.get("scheduled_at", "").strip()
    if not when_str:
        flash("A schedule time is required.")
        return redirect(url_for("dashboard"))
    try:
        when = datetime.strptime(when_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Invalid time format.")
        return redirect(url_for("dashboard"))
    if when <= datetime.now(timezone.utc).replace(tzinfo=None):
        flash("Schedule time must be in the future (UTC).")
        return redirect(url_for("dashboard"))
    c.scheduled_at = when
    db.session.commit()
    scheduler.add_job(run_blast_job, "date", run_date=when,
                     args=[c.id], id=f"blast_{c.id}", replace_existing=True)
    flash(f"Campaign {c.id} scheduled for {when.isoformat()} UTC.")
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
