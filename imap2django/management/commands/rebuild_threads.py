from django.core.management.base import BaseCommand
from imap2django.services.threading import rebuild_threads

class Command(BaseCommand):
    help = "Assign/rebuild Thread objects for Messages."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **opts):
        count = rebuild_threads(limit=opts["limit"])
        self.stdout.write(self.style.SUCCESS(f"Threads rebuilt for {count} messages"))
