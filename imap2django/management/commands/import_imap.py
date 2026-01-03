import json
from django.core.management.base import BaseCommand
from imap2django.services.imap_client import ImapClient, ImapConfig
from imap2django.services.parser import parse_rfc822, parse_date_to_dt
from imap2django.services.normalizer import normalize
from imap2django.services.checkpoint import get_checkpoint, set_checkpoint
from imap2django.loaders.sql_loader import load_sql
from imap2django.loaders.neo4j_loader import load_neo4j
from datetime import timezone as dt_timezone
from django.utils import timezone

class Command(BaseCommand):
    help = "Import emails from IMAP into Django SQL models or Neo4j (streaming + checkpoint)."

    def add_arguments(self, parser):
        parser.add_argument("--config", required=True, help="Path to account config JSON file")
        parser.add_argument("--backend", choices=["sql", "neo4j"], default="sql")
        parser.add_argument("--folders", default="", help="Comma-separated folders (default: all)")
        parser.add_argument("--batch", type=int, default=200)
        parser.add_argument("--resume", action="store_true", help="Resume from checkpoint (default behavior)")
        parser.add_argument("--max", type=int, default=0, help="Max messages per folder (0 = no limit)")

    def handle(self, *args, **opts):
        cfg_path = opts["config"]
        backend = opts["backend"]
        batch_size = opts["batch"]
        folder_filter = [f.strip() for f in opts["folders"].split(",") if f.strip()]
        max_per_folder = opts["max"]

        with open(cfg_path, "r", encoding="utf-8") as f:
            account_cfg = json.load(f)

        account_email = account_cfg["account_email"]
        provider = account_cfg.get("provider", "")
        imap_cfg = ImapConfig(
            host=account_cfg["imap"]["host"],
            port=int(account_cfg["imap"].get("port", 993)),
            ssl=bool(account_cfg["imap"].get("ssl", True)),
            username=account_cfg["imap"]["username"],
            password=account_cfg["imap"]["password"],
        )

        self.stdout.write(self.style.SUCCESS(f"Starting import for {account_email} (backend={backend})"))

        with ImapClient(imap_cfg) as imap:
            folders = imap.list_folders()
            if folder_filter:
                folders = [f for f in folders if f in folder_filter]

            self.stdout.write(f"Folders: {folders}")

            total = 0
            for folder in folders:
                self.stdout.write(self.style.MIGRATE_HEADING(f"== Folder: {folder} =="))
                try:
                    imap.select_folder(folder)
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Skipping folder '{folder}' (not selectable): {e}")
                    )
                    continue


                # Checkpoint stored in SQL tables (even if backend=neo4j, simplest approach)
                from imap2django.models import Account
                account_obj, _ = Account.objects.get_or_create(email=account_email, defaults={"provider": provider})
                last_uid = get_checkpoint(account_obj, folder)

                uids = imap.search_uids_since(last_uid)
                uids = sorted(uids)

                if not uids:
                    self.stdout.write("No new messages.")
                    continue

                processed_in_folder = 0

                for i in range(0, len(uids), batch_size):
                    batch_uids = uids[i:i+batch_size]
                    fetched = imap.fetch_batch(batch_uids)

                    # process each uid in the batch
                    max_uid_in_batch = last_uid
                    for uid in batch_uids:
                        item = fetched.get(uid) or {}
                        raw = item.get(b"RFC822") or item.get("RFC822") or b""
                        # flags = item.get(b"FLAGS") or item.get("FLAGS") or []
                        raw_flags = item.get(b"FLAGS") or item.get("FLAGS") or []
                        flags = [
                            f.decode("utf-8", errors="ignore") if isinstance(f, (bytes, bytearray)) else str(f)
                            for f in raw_flags
                        ]
                            
                        internal_date = item.get(b"INTERNALDATE") or item.get("INTERNALDATE")
                        if internal_date and timezone.is_naive(internal_date):
                            internal_date = timezone.make_aware(internal_date, dt_timezone.utc)

                        size = item.get(b"RFC822.SIZE") or item.get("RFC822.SIZE") or 0

                        if not raw:
                            continue

                        parsed = parse_rfc822(raw)
                        date_dt = parse_date_to_dt(parsed.date or "")
                        norm = normalize(parsed, raw, size=size, date_dt=date_dt)

                        if backend == "sql":
                            load_sql(
                                account_email=account_email,
                                provider=provider,
                                mailbox_name=folder,
                                uid=uid,
                                flags=flags,
                                internal_date=internal_date,
                                normalized=norm,
                            )
                        else:
                            load_neo4j(
                                account_email=account_email,
                                provider=provider,
                                mailbox_name=folder,
                                uid=uid,
                                flags=flags,
                                internal_date=internal_date,
                                normalized=norm,
                            )

                        processed_in_folder += 1
                        total += 1
                        if uid > max_uid_in_batch:
                            max_uid_in_batch = uid

                        if max_per_folder and processed_in_folder >= max_per_folder:
                            break

                    # checkpoint after each batch
                    if max_uid_in_batch > last_uid:
                        set_checkpoint(account_obj, folder, max_uid_in_batch)
                        last_uid = max_uid_in_batch

                    self.stdout.write(f"Batch done. checkpoint last_uid={last_uid}, folder_count={processed_in_folder}")

                    if max_per_folder and processed_in_folder >= max_per_folder:
                        self.stdout.write("Reached --max limit for folder.")
                        break

        self.stdout.write(self.style.SUCCESS(f"Import finished. Total processed: {total}"))
