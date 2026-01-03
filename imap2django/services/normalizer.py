from dataclasses import dataclass
from typing import List, Tuple
from ..utils import norm_email, norm_subject, sha256_bytes

@dataclass
class NormalizedEmail:
    raw_sha256: str
    message_id: str
    content_fingerprint: str
    subject: str
    subject_norm: str
    date_dt: object
    from_name: str
    from_email_norm: str
    to_norm: List[Tuple[str, str]]
    cc_norm: List[Tuple[str, str]]
    bcc_norm: List[Tuple[str, str]]
    in_reply_to: str
    references: List[str]
    body_text: str
    body_html: str
    attachments: list
    size: int

def compute_content_fingerprint(subject_norm: str, from_email: str, body_text: str) -> str:
    # Small stable “semantic-ish” hash (not perfect, but useful fallback).
    snippet = (body_text or "")[:2000]
    payload = f"{subject_norm}|{from_email}|{snippet}".encode("utf-8", errors="replace")
    return sha256_bytes(payload)

def normalize(parsed, raw_bytes: bytes, size: int, date_dt):
    from_email_norm = norm_email(parsed.from_email)
    subject_norm = norm_subject(parsed.subject)

    to_norm = [(n, norm_email(e)) for n, e in parsed.to if e]
    cc_norm = [(n, norm_email(e)) for n, e in parsed.cc if e]
    bcc_norm = [(n, norm_email(e)) for n, e in parsed.bcc if e]

    raw_sha = sha256_bytes(raw_bytes)
    content_fp = compute_content_fingerprint(subject_norm, from_email_norm, parsed.body_text)

    return NormalizedEmail(
        raw_sha256=raw_sha,
        message_id=(parsed.message_id or "").strip(),
        content_fingerprint=content_fp,
        subject=parsed.subject,
        subject_norm=subject_norm,
        date_dt=date_dt,
        from_name=parsed.from_name,
        from_email_norm=from_email_norm,
        to_norm=to_norm,
        cc_norm=cc_norm,
        bcc_norm=bcc_norm,
        in_reply_to=(parsed.in_reply_to or "").strip(),
        references=parsed.references or [],
        body_text=parsed.body_text or "",
        body_html=parsed.body_html or "",
        attachments=parsed.attachments or [],
        size=size,
    )
