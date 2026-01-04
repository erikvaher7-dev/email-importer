from django.db import transaction
from ..models import Person, Message, Recipient, Attachment
from ..utils import norm_email

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
    """
    Returns (message, created_bool)
    """
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
            Attachment.objects.create(
                message=msg,
                filename=a.filename or "",
                content_type=a.content_type or "",
                size=a.size or 0,
                part_id=a.part_id or "",
            )

    return msg, created
