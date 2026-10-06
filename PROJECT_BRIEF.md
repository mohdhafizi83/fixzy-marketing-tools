# Fixzy Marketing Tools — Project Brief

Status: PLANNING (development belum mula) · Dimulakan: 6 Okt 2026 · Owner: Hafizi (AI Agentic for Hire)
Profile Hermes: `fixzymarketingtool` (khusus projek ini sahaja) · Port sasaran: **:5558** (verified kosong)

## 1. Apa ini

Open-source portfolio tool: lead generation + multi-channel outreach. Rebuild moden
bagi legacy app "EmailSpider" (VB.NET, Visual Studio 2015, .NET Framework 4.5.2,
last commit 17 Okt 2016) yang berada di external HD:

    /mnt/workstation/Projects/standalone/Visual Studio 2015/Projects/FixzyMarketingTools/
    (NTFS "Workstation" — mount read-only: sudo mount -o ro /dev/sdb1 /mnt/workstation)

## 2. Features legacy yang dikekalkan (dari bacaan kod penuh, Okt 2026)

- Extract EMAIL + TELEFON dari 4 sumber: fail .txt/.csv, senarai URL, text paste, crawl seluruh website (ikut `<a href>`)
- Phone normalization Malaysia: country code `6`, prefix `01`, buang karakter sampah (`-`, space, dsb)
- Dedup hasil semasa scrape
- Export ke TXT/CSV
- Blast email via SMTP (SendGrid) dan SMS via HTTP gateway
- Settings form untuk credential

## 3. Yang DIBUANG / DIGANTI

| Legacy | Kenapa | Gantian |
|---|---|---|
| Google search scrape `<cite>` | Sudah mati — Google block | Search API (SerpAPI ~$0.0008/search) atau SearXNG |
| sms99.net | Gateway dah lama tiada | Gateway SMS MY baru: Twilio / RedSMS / TMTxcel (~RM0.04–0.10/pesan) |
| Expiry hardcoded 1 Dis 2017 | App dulu dijual berkunci | Buang — open source |
| WinForms desktop Windows | Platform terikat | Web UI (Flask), jalan atas Linux server |
| Credential plain text dalam config | Risiko keselamatan | .env + template; secrets tak masuk git |

## 4. Features BARU

- **Consent ledger + auto-unsubscribe** pada setiap outbound (PDPA 2010 Malaysia — denda hingga RM500k). Ini feature, bukan beban.
- **Suppression list** automatik (email bounce / unsub → tak diganggu lagi)
- **Campaign analytics** — delivered / opened / failed per channel
- **AI copy drafts** — draft mesej guna local LLM `localhost:8080` (kos RM0)
- **Channel capability flags** — setiap channel ditanda apa ia benar-benar boleh buat (lihat §6)

## 5. Tech stack (dipersetujui 6 Okt 2026)

- Flask + Jinja/HTMX (web UI) — konsisten dengan ekosistem Flask sedia ada (:5556, :5557)
- SQLite — leads, campaigns, consent, suppression
- APScheduler — jadual blast + rate limiting
- selectolax / requests — crawler (ganti HtmlAgilityPack)
- aiosmtplib — email sender
- **Adapter pattern**: `adapters/sendgrid.py`, `adapters/twilio_sms.py`, `adapters/telegram.py`, `adapters/whatsapp_cloud.py`
  — satu interface: `send(lead, message, channel)`
- Port **:5558**, systemd user unit `fixzy-marketing-tools.service` (bila deploy)

## 6. Realiti channel (verified vs docs rasmi, Okt 2026)

JANGAN bina "blast button" untuk channel yang tak menyokong outbound — ban risk.

**TIER 1 — outbound automatik dibenar:**
- Email: Brevo (300/jam free) / SendGrid (100/jam free) / Resend (3k/bulan free)
- SMS MY: Twilio / RedSMS / TMTxcel ~RM0.04–0.10/pesan
- Telegram Bot: RM0 — tapi hanya kepada user yang dah `/start`

**TIER 2 — reply-only (24-hour window selepas user mesej kita):**
- WhatsApp Cloud API (Meta): marketing template ~RM0.50/mesej (MY, sejak Jul 2025); perlu Meta Business verification + template approval; cold blast = nombor senang kena ban
- Facebook Messenger / Instagram DM: TIADA API untuk DM orang asing; Private Replies untuk reply comment (7 hari)

**TIER 3 — publish/monitor sahaja (tiada DM API):**
- X/Twitter: pay-per-use ~$0.005/post read; boleh post + auto-reply comment
- TikTok / YouTube: API untuk upload + baca comment/insights sahaja

## 7. Fasa

- **F1 (MVP, ~RM0):** crawler + lead DB + Email + Telegram + unsubscribe handling
- **F2:** SMS gateway MY + search API + analytics dashboard
- **F3:** WhatsApp Cloud API + FB/IG reply inbox + X/TikTok comment monitoring

> KEPUTUSAN SAH (6 Okt 2026, owner): F1 = crawler + lead DB + Email + Telegram
> + consent ledger/auto-unsubscribe. Provider email: **Brevo** (300/jam free).
> GitHub: develop local dulu, public kemudian.

## 8. Amaran keselamatan

- `akaun_detail.png` dalam folder legacy **mendedahkan credential SendGrid/SMS lama** plain text — JANGAN publish/share; anggap sudah bocor.
- Tiada API key sebenar masuk git. `.env` untuk secrets, `.env.example` untuk template.

## 9. Cara mula sesi development

    fixzymarketingtool chat
    # atau: hermes -p fixzymarketingtool chat

Working directory profil sudah ditetapkan ke /home/fizi/projects/fixzy-marketing-tools/.
Baca fail ini dahulu, kemudian mula F1.
