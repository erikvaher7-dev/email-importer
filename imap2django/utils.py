import hashlib
import re

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def norm_email(email: str) -> str:
    return (email or "").strip().lower()

SUBJECT_PREFIX_RE = re.compile(r"^(\s*(re|fwd|fw)\s*:\s*)+", re.IGNORECASE)

def norm_subject(subject: str) -> str:
    s = (subject or "").strip()
    s = SUBJECT_PREFIX_RE.sub("", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s.lower()
