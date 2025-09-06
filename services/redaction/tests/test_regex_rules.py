import re
from services.redaction.detectors import regex_rules as rr

def _matches(pattern, text, flags=re.IGNORECASE):
    return re.findall(re.compile(pattern, flags), text)

def test_email_detects():
    text = "Contact me at therapist@example.com or admin@clinic.org"
    assert _matches(rr.EMAIL, text)

def test_phone_detects():
    text = "Call 555-123-4567 or (555) 987-6543."
    assert _matches(rr.PHONE, text)

def test_ssn_detects():
    text = "SSN 123-45-6789."
    assert _matches(rr.SSN, text)