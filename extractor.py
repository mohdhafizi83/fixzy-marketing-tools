"""Lead extraction + normalization — mirrors the legacy EmailSpider Form4.vb logic.

Legacy reference (Form4.vb line ~612, Settings.Designer.vb):
  phone_country=6, phone_firsttwo=01, phone_replacechar=" -"
  A number is accepted if it starts with "+601" / "601" / "01"
  after the junk characters are stripped.
"""
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Strip every non-digit (legacy only stripped " -"; stripping all is safer)
NON_DIGIT_RE = re.compile(r"\D+")


def extract_emails(text: str) -> list[str]:
    """Unique emails, lowercased, in first-appearance order."""
    seen: set[str] = set()
    out: list[str] = []
    for m in EMAIL_RE.findall(text or ""):
        e = m.lower().strip(".")
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def normalize_phone_my(raw: str) -> str | None:
    """Normalize a Malaysian phone number to 601XXXXXXXX format.

    Returns None if the input is not a valid Malaysian mobile number
    (must start with 601 or 01 after normalization).
    """
    digits = NON_DIGIT_RE.sub("", raw or "")
    if digits.startswith("006"):          # 00601... -> 601...
        digits = digits[2:]
    if digits.startswith("601"):
        return digits if 10 <= len(digits) <= 12 else None
    if digits.startswith("01"):
        return "6" + digits               # 0123456789 -> 60123456789
    return None


def extract_phones_my(text: str) -> list[str]:
    """Unique normalized Malaysian mobile numbers."""
    seen: set[str] = set()
    out: list[str] = []
    # Candidates: digit sequences with common separators (+ - space, parentheses)
    for cand in re.findall(r"[+()0-9][0-9 ()\-]{6,}", text or ""):
        n = normalize_phone_my(cand)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out
