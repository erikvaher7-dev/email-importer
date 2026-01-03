from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from email.parser import BytesParser
from email import policy
from email.message import Message as EmailMessage
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

@dataclass
class ParsedAttachment:
    filename: str
    content_type: str
    size: int
    part_id: str

@dataclass
class ParsedEmail:
    message_id: str
    subject: str
    date: Optional[str]
    from_name: str
    from_email: str
    to: List[Tuple[str, str]]
    cc: List[Tuple[str, str]]
    bcc: List[Tuple[str, str]]
    in_reply_to: str
    references: List[str]
    body_text: str
    body_html: str
    attachments: List[ParsedAttachment]

def _parse_address_list(msg: EmailMessage, header: str) -> List[Tuple[str, str]]:
    values = msg.get_all(header, [])
    result: List[Tuple[str, str]] = []
    from email.utils import getaddresses
    for name, email in getaddresses(values):
        if email:
            result.append((name or "", email))
    return result

def _get_from(msg: EmailMessage) -> Tuple[str, str]:
    from email.utils import parseaddr
    name, email = parseaddr(msg.get("From", "") or "")
    return (name or "", email or "")

def _extract_bodies(msg: EmailMessage) -> Tuple[str, str, List[ParsedAttachment]]:
    body_text = ""
    body_html = ""
    attachments: List[ParsedAttachment] = []

    if msg.is_multipart():
        for i, part in enumerate(msg.walk()):
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            filename = part.get_filename() or ""
            is_attachment = "attachment" in disp or (filename != "")

            if is_attachment:
                payload = part.get_payload(decode=True) or b""
                attachments.append(ParsedAttachment(
                    filename=filename,
                    content_type=ctype,
                    size=len(payload),
                    part_id=str(i),
                ))
                continue

            if ctype == "text/plain" and not body_text:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                try:
                    body_text = payload.decode(charset, errors="replace")
                except Exception:
                    body_text = payload.decode("utf-8", errors="replace")

            if ctype == "text/html" and not body_html:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                try:
                    body_html = payload.decode(charset, errors="replace")
                except Exception:
                    body_html = payload.decode("utf-8", errors="replace")
    else:
        ctype = msg.get_content_type()
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if ctype == "text/html":
            body_html = text
        else:
            body_text = text

    # If no plain text but have html, derive text
    if not body_text and body_html:
        soup = BeautifulSoup(body_html, "lxml")
        body_text = soup.get_text("\n")

    return body_text, body_html, attachments

def parse_rfc822(raw_bytes: bytes) -> ParsedEmail:
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)

    message_id = (msg.get("Message-ID", "") or "").strip()
    subject = (msg.get("Subject", "") or "").strip()
    date_raw = (msg.get("Date", "") or "").strip()

    from_name, from_email = _get_from(msg)
    to_list = _parse_address_list(msg, "To")
    cc_list = _parse_address_list(msg, "Cc")
    bcc_list = _parse_address_list(msg, "Bcc")

    in_reply_to = (msg.get("In-Reply-To", "") or "").strip()
    references = []
    refs = (msg.get("References", "") or "").strip()
    if refs:
        references = [r.strip() for r in refs.split() if r.strip()]

    body_text, body_html, attachments = _extract_bodies(msg)

    return ParsedEmail(
        message_id=message_id,
        subject=subject,
        date=date_raw,
        from_name=from_name,
        from_email=from_email,
        to=to_list,
        cc=cc_list,
        bcc=bcc_list,
        in_reply_to=in_reply_to,
        references=references,
        body_text=body_text,
        body_html=body_html,
        attachments=attachments,
    )

def parse_date_to_dt(date_str: str):
    if not date_str:
        return None
    try:
        return dateparser.parse(date_str)
    except Exception:
        return None
