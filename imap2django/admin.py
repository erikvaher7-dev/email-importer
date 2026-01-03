from django.contrib import admin
from .models import Account, Mailbox, Person, Message, MailboxMessage, Thread, Attachment, Recipient, ImportCheckpoint

admin.site.register(Account)
admin.site.register(Mailbox)
admin.site.register(Person)
admin.site.register(Message)
admin.site.register(MailboxMessage)
admin.site.register(Thread)
admin.site.register(Attachment)
admin.site.register(Recipient)
admin.site.register(ImportCheckpoint)
