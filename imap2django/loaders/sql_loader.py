from django.db import transaction
from ..models import Account, Mailbox, MailboxMessage
from ..services.dedup import upsert_message_and_relations

@transaction.atomic
def ensure_account_and_mailbox(account_email: str, provider: str, mailbox_name: str):
    account, _ = Account.objects.get_or_create(email=account_email, defaults={"provider": provider or ""})
    mailbox, _ = Mailbox.objects.get_or_create(account=account, name=mailbox_name)
    return account, mailbox

@transaction.atomic
def link_mailbox_message(mailbox, message, uid: int, flags: list, modseq=None):
    MailboxMessage.objects.update_or_create(
        mailbox=mailbox,
        uid=uid,
        defaults={"message": message, "flags_json": list(flags or []), "modseq": modseq}
    )

def load_sql(account_email: str, provider: str, mailbox_name: str, uid: int, flags, internal_date, normalized):
    account, mailbox = ensure_account_and_mailbox(account_email, provider, mailbox_name)
    msg, _created = upsert_message_and_relations(normalized, internal_date=internal_date)
    link_mailbox_message(mailbox, msg, uid=uid, flags=flags or [], modseq=None)
    return account, mailbox, msg
