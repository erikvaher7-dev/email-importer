from django.db import models

class Account(models.Model):
    email = models.EmailField(unique=True)
    provider = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class Mailbox(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="mailboxes")
    name = models.CharField(max_length=255)
    delimiter = models.CharField(max_length=8, blank=True, default="/")

    class Meta:
        unique_together = [("account", "name")]

    def __str__(self):
        return f"{self.account.email}:{self.name}"

class Person(models.Model):
    # person_hash = stable identity key (e.g., normalized primary email)
    person_hash = models.CharField(max_length=128, unique=True)
    primary_email = models.EmailField()
    display_name = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.primary_email

class Thread(models.Model):
    thread_key = models.CharField(max_length=128, unique=True)
    subject_norm = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    raw_sha256 = models.CharField(max_length=64, unique=True)
    message_id = models.CharField(max_length=512, blank=True, null=True, db_index=True)
    content_fingerprint = models.CharField(max_length=64, db_index=True)

    subject = models.CharField(max_length=998, blank=True, default="")
    subject_norm = models.CharField(max_length=998, blank=True, default="")

    date = models.DateTimeField(blank=True, null=True)
    internal_date = models.DateTimeField(blank=True, null=True)

    in_reply_to = models.CharField(max_length=512, blank=True, default="")
    references_json = models.JSONField(blank=True, default=list)

    body_text = models.TextField(blank=True, default="")
    body_html = models.TextField(blank=True, default="")
    size = models.IntegerField(default=0)

    thread = models.ForeignKey(Thread, on_delete=models.SET_NULL, null=True, blank=True, related_name="messages")

    created_at = models.DateTimeField(auto_now_add=True)

class MailboxMessage(models.Model):
    mailbox = models.ForeignKey(Mailbox, on_delete=models.CASCADE, related_name="mailbox_messages")
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="mailbox_messages")

    uid = models.BigIntegerField()
    flags_json = models.JSONField(blank=True, default=list)
    modseq = models.BigIntegerField(blank=True, null=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("mailbox", "uid")]

class Recipient(models.Model):
    TO = "to"
    CC = "cc"
    BCC = "bcc"
    TYPES = [(TO, "TO"), (CC, "CC"), (BCC, "BCC")]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="recipients")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="received_messages")
    type = models.CharField(max_length=8, choices=TYPES)

class Attachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    filename = models.CharField(max_length=512, blank=True, default="")
    content_type = models.CharField(max_length=255, blank=True, default="")
    size = models.IntegerField(default=0)
    part_id = models.CharField(max_length=64, blank=True, default="")
    sha256 = models.CharField(max_length=64, blank=True, default="")
    storage_url = models.CharField(max_length=1024, blank=True, default="")

class ImportCheckpoint(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="checkpoints")
    mailbox_name = models.CharField(max_length=255)
    last_uid = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("account", "mailbox_name")]
