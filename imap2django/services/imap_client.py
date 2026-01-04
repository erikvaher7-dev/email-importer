from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Iterable, Tuple
from imapclient import IMAPClient

@dataclass
class ImapConfig:
    host: str
    port: int = 993
    ssl: bool = True
    username: str = ""
    password: str = ""

class ImapClient:
    def __init__(self, cfg: ImapConfig):
        self.cfg = cfg
        self.client: Optional[IMAPClient] = None

    def __enter__(self):
        self.client = IMAPClient(self.cfg.host, port=self.cfg.port, ssl=self.cfg.ssl)
        self.client.login(self.cfg.username, self.cfg.password)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.client:
            try:
                self.client.logout()
            except Exception:
                pass

    def list_folders(self) -> List[str]:
        assert self.client
        folders = []
        for flags, delimiter, name in self.client.list_folders():
            folders.append(name)
        return folders

    def select_folder(self, folder: str):
        assert self.client
        self.client.select_folder(folder, readonly=True)

    def search_uids_since(self, last_uid: int) -> List[int]:
        """
        Fetch UIDs > last_uid. We do it as a UID range query.
        """
        assert self.client
        # UID ranges are inclusive. Use (last_uid+1):*
        start = last_uid + 1
        return self.client.search([u"UID", f"{start}:*"])

    def fetch_batch(self, uids: List[int]) -> Dict[int, Dict[str, Any]]:
        assert self.client
        if not uids:
            return {}
        # RFC822 gives raw bytes; FLAGS and INTERNALDATE are metadata
        return self.client.fetch(uids, ["RFC822", "FLAGS", "INTERNALDATE", "RFC822.SIZE"])
