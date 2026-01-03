from ..models import ImportCheckpoint, Account

def get_checkpoint(account: Account, mailbox_name: str) -> int:
    cp, _ = ImportCheckpoint.objects.get_or_create(
        account=account,
        mailbox_name=mailbox_name,
        defaults={"last_uid": 0}
    )
    return cp.last_uid

def set_checkpoint(account: Account, mailbox_name: str, last_uid: int):
    ImportCheckpoint.objects.update_or_create(
        account=account,
        mailbox_name=mailbox_name,
        defaults={"last_uid": last_uid}
    )
