from django.db import transaction
from django.utils import timezone
from ..models import Person, Message, Recipient, Attachment, MessageAttachment
from ..utils import norm_email, sha256_bytes
from ..services.storage import storage_backend

def upsert_person(email_norm: str, display_name: str = "") -> Person:
    key = email_norm
    obj, _ = Person.objects.get_or_create(
        person_hash=key,
        defaults={"primary_email": email_norm, "display_name": display_name or ""}
    )
    # Keep best display name if we get a better one later
    if display_name and not obj.display_name:
        obj.display_name = display_name
        obj.save(update_fields=["display_name"])
    return obj

@transaction.atomic
def upsert_message_and_relations(n, internal_date=None):
    msg, created = Message.objects.get_or_create(
        raw_sha256=n.raw_sha256,
        defaults={
            "message_id": n.message_id or None,
            "content_fingerprint": n.content_fingerprint,
            "subject": n.subject,
            "subject_norm": n.subject_norm,
            "date": n.date_dt,
            "internal_date": internal_date,
            "in_reply_to": n.in_reply_to,
            "references_json": n.references,
            "body_text": n.body_text,
            "body_html": n.body_html,
            "size": n.size,
        }
    )
    
    if not created and not msg.content_fingerprint:
        msg.content_fingerprint = n.content_fingerprint
        msg.save(update_fields=["content_fingerprint"])
    
    if created:
        from ..services.chunking import chunker
        chunker.store_chunks(msg, n.body_text, n.body_html)

    # If it already existed, we still might want to update missing message_id
    if not created and n.message_id and not msg.message_id:
        msg.message_id = n.message_id
        msg.save(update_fields=["message_id"])

    # Only create recipients/attachments if newly created (avoid duplicates)
    if created:
        # Sender as Person (optional; keeping it useful)
        if n.from_email_norm:
            upsert_person(n.from_email_norm, n.from_name)

        for name, email in n.to_norm:
            if email:
                p = upsert_person(email, name)
                Recipient.objects.create(message=msg, person=p, type=Recipient.TO)

        for name, email in n.cc_norm:
            if email:
                p = upsert_person(email, name)
                Recipient.objects.create(message=msg, person=p, type=Recipient.CC)

        for name, email in n.bcc_norm:
            if email:
                p = upsert_person(email, name)
                Recipient.objects.create(message=msg, person=p, type=Recipient.BCC)

        for a in n.attachments:
            attachment, _ = Attachment.objects.get_or_create(
                sha256=a.sha256,
                defaults={
                    'filename': a.filename or "",
                    'content_type': a.content_type or "",
                    'size': a.size or 0,
                    'storage_path': storage_backend.store(a.payload, a.sha256),
                }
            )
            if not _:
                attachment.last_seen_at = timezone.now()
                attachment.save(update_fields=['last_seen_at'])
            
            MessageAttachment.objects.get_or_create(
                message=msg,
                attachment=attachment,
                part_id=a.part_id or "",
            )

    return msg, created
