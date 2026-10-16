# PDPA Compliance Guide (Malaysia)

Practical guide to using this tool in line with Malaysia's **Personal Data
Protection Act 2010 (Act 709)** ("PDP Act"), which came into force on
15 November 2017 and is administered by the Personal Data Protection
Department (Jabatan Perlindungan Data Peribadi, JPDP) — official portal:
[pdp.gov.my](https://www.pdp.gov.my).

> **This is not legal advice.** It is an operator's guide to the compliance
> features this tool provides. The Act has been amended since 2010 — always
> check the current text and JPDP guidance, and consult a Malaysian lawyer
> for your specific situation.

## What the PDP Act requires (basics)

- **Scope.** The Act regulates *personal data* processed in respect of
  *commercial transactions* by a *data user* carrying on business in Malaysia.
  It does not bind the federal/state governments or personal/household use.
- **Seven personal data protection principles** (ss. 6–12 of the Act):
  1. **General** — do not process personal data without the data subject's
     consent (subject to other lawful bases such as contract or legal duty).
  2. **Notice and Choice** — tell the subject what data you hold, why, and
     give them a way to opt out.
  3. **Disclosure** — do not disclose data except for the disclosed purpose
     or with consent.
  4. **Security** — protect data against loss, misuse, modification,
     unauthorised access.
  5. **Retention** — do not keep data longer than necessary for the purpose.
  6. **Data Integrity** — keep data accurate and up to date.
  7. **Access** — let subjects access and correct their data on request.
- **Direct marketing opt-out.** A data subject can serve written notice
  requiring you to stop processing their data for direct marketing (s. 15 of
  the Act). Honour it immediately — this is exactly what the unsubscribe link
  in this tool implements.
- **Penalties.** Breaching the protection principles can mean a fine up to
  **RM300,000 and/or up to 2 years' imprisonment** (s. 5(2)). Check the
  current amounts — amendments have raised some penalties.
- **Cross-border transfer** (s. 129 + 2019 transfer regulations): transferring
  personal data outside Malaysia needs a lawful basis (e.g. consent, adequate
  safeguards). Using foreign cloud providers (Brevo, Twilio, Meta) is a
  transfer — factor this into your notice/consent wording.
- **Data user registration.** Certain categories of data users must register
  with JPDP. Check the current exemption order for whether you must.

## How this tool maps to those duties

### 1. Consent ledger (General + Notice/Choice principles)

Every send is gated on an **active consent record** for that channel:

```
consent: lead_id | channel | granted_at | granted_source | revoked_at
```

- A campaign blast to `email` only reaches leads with an unrevoked `email`
  consent; same for `telegram`, `sms`, etc. Leads without consent are skipped
  and the skip is reported.
- `granted_source` records *how* consent was obtained (`import_file`,
  `telegram_start`, `e2e_test`, …) — your audit trail for "prove your consent".
- **You are responsible for the consent behind imported lists.** Importing a
  CSV creates consent records because you assert the list was collected with
  consent (opt-in). Do not import scraped or bought lists and expect the tool
  to absolve you — see the crawler note below.

### 2. Suppression list + auto-unsubscribe (opt-out duty)

- Every outbound message carries a one-click unsubscribe link
  (`PUBLIC_BASE_URL/unsubscribe/<token>`) — no login required for recipients.
- Confirming an unsubscribe **revokes consent for that channel and adds the
  contact to the suppression list**. Suppressed contacts are excluded from all
  future sends on that channel, permanently.
- Keep suppression records as long as you keep the ability to contact people —
  deleting them risks re-contacting people who opted out.

### 3. Crawled / discovered leads — the trap

The crawler and search discovery create leads **without** consent records, so
the send gate blocks them by default. That is deliberate: a publicly listed
business email is *not* consent for direct marketing under the Act. Contact
them via an invited channel (reply window, form submission, /start) first, or
obtain consent another way.

### 4. Security, retention, access

- Set `ADMIN_PASSWORD`, serve behind HTTPS (reverse proxy), and treat
  `fixzy.db` as personal data: it is gitignored — never commit or share it.
- Retention: delete leads/campaigns you no longer need (Retention principle).
  The Leads page has CSV/TXT export if a subject requests a copy (Access
  principle); correct data on request (Data Integrity).
- Webhooks that feed analytics are signature-verified (Brevo secret, Telegram
  secret token) so third parties cannot forge events into your records.

### 5. Operator checklist

- [ ] `SECRET_KEY` and `ADMIN_PASSWORD` set; app behind HTTPS.
- [ ] Every imported list has a documented opt-in source (`granted_source`).
- [ ] Unsubscribe works end-to-end (test it after changing `PUBLIC_BASE_URL`).
- [ ] Sender identity in messages matches your business (Notice principle).
- [ ] Periodic retention sweep: delete stale leads and old campaign data.
- [ ] Check JPDP registration/cross-border obligations for your business.
