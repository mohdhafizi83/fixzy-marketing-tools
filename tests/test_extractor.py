"""Extractor tests: email regex + Malaysian phone normalization.

Phone cases mirror legacy Form4.vb behavior (brief section 2):
strip non-digits, accept +601/601/01 prefixes, output 601XXXXXXXX.
"""
from extractor import extract_emails, extract_phones_my


def test_extract_basic_email():
    assert "john@example.com" in extract_emails("contact john@example.com now")


def test_extract_email_lowercase():
    found = extract_emails("MAIL TO: John.Doe@Example.COM")
    assert "john.doe@example.com" in found


def test_extract_multiple_emails_deduped():
    text = "a@x.com and b@y.com and a@x.com"
    found = list(extract_emails(text))
    assert len(found) == len(set(found)) == 2


def test_phone_mobile_01_prefix():
    assert "60123456789" in extract_phones_my("call 012-345 6789")


def test_phone_mobile_plus60():
    assert "60123456789" in extract_phones_my("+60 12-345 6789")


def test_phone_already_normalized():
    assert "60123456789" in extract_phones_my("60123456789")


def test_phone_0060_intl_dial():
    assert "60123456789" in extract_phones_my("0060123456789")


def test_phone_rejects_landline():
    # 3xx landlines are not valid mobile numbers (legacy rule: prefix 01 only)
    assert "60322223333" not in extract_phones_my("03-2222 3333")


def test_phone_rejects_short_numbers():
    assert extract_phones_my("12345") == []
