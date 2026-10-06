"""Extraction + normalisasi lead — padan logik legacy EmailSpider Form4.vb.

Legacy (Form4.vb m/s 612, Settings.Designer.vb):
  phone_country=6, phone_firsttwo=01, phone_replacechar=" -"
  Diterima jika bermula "+601" / "601" / "01" selepas buang char sampah.
"""
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Semua bukan digit dibuang (legacy buang " -"; kita buang semua sampah — lebih selamat)
NON_DIGIT_RE = re.compile(r"\D+")


def extract_emails(text: str) -> list[str]:
    """Senarai email unik, lowercase, tertib kemunculan pertama."""
    seen: set[str] = set()
    out: list[str] = []
    for m in EMAIL_RE.findall(text or ""):
        e = m.lower().strip(".")
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def normalize_phone_my(raw: str) -> str | None:
    """Normalisasi nombor telefon Malaysia ke format 601XXXXXXXX.

    Return None jika bukan nombor MY yang sah (bukan 601/01 selepas dinormalisasi).
    """
    digits = NON_DIGIT_RE.sub("", raw or "")
    if digits.startswith("006"):          # 00601... → 601...
        digits = digits[2:]
    if digits.startswith("601"):
        return digits if 10 <= len(digits) <= 12 else None
    if digits.startswith("01"):
        return "6" + digits               # 0123456789 → 60123456789
    return None


def extract_phones_my(text: str) -> list[str]:
    """Nombor MY unik yang telah dinormalisasi."""
    seen: set[str] = set()
    out: list[str] = []
    # calon: jujukan digit dgn pemisah lazim (+ - spasi kurungan)
    for cand in re.findall(r"[+()0-9][0-9 ()\-]{6,}", text or ""):
        n = normalize_phone_my(cand)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out
