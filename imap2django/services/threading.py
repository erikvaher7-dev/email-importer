from ..models import Message, Thread
from django.db import transaction
import hashlib

def _thread_key_for_message(msg: Message) -> str:
    """
    Header-first approach:
    - If references exist => hash of first reference (often root)
    - Else if in_reply_to exists => hash of that
    - Else fallback => hash of normalized subject + sender + date bucket
    """
    refs = msg.references_json or []
    if refs:
        root = refs[0]
        return hashlib.sha256(f"ref:{root}".encode("utf-8")).hexdigest()[:40]

    if msg.in_reply_to:
        return hashlib.sha256(f"irt:{msg.in_reply_to}".encode("utf-8")).hexdigest()[:40]

    # fallback
    sender = ""
    # we stored sender person separately but not linked; keep simple fallback:
    subject = msg.subject_norm or ""
    bucket = (msg.date.date().isoformat() if msg.date else "nodate")
    return hashlib.sha256(f"fallback:{subject}:{bucket}:{sender}".encode("utf-8")).hexdigest()[:40]

@transaction.atomic
def rebuild_threads(limit: int = 0):
    qs = Message.objects.all().order_by("id")
    if limit and limit > 0:
        qs = qs[:limit]

    count = 0
    for msg in qs.iterator(chunk_size=500):
        tkey = _thread_key_for_message(msg)
        thread, _ = Thread.objects.get_or_create(
            thread_key=tkey,
            defaults={"subject_norm": msg.subject_norm or ""}
        )
        if msg.thread_id != thread.id:
            msg.thread = thread
            msg.save(update_fields=["thread"])
        count += 1
    return count
