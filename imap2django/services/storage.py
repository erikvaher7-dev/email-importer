from pathlib import Path
from django.conf import settings
from ..exceptions import StorageError

class AttachmentStorage:
    def __init__(self, base_path=None):
        self.base_path = Path(base_path or getattr(settings, 'ATTACHMENT_STORAGE_PATH', 'attachments'))
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def store(self, content: bytes, sha256: str) -> str:
        path = self.base_path / sha256[:2] / sha256[2:4] / sha256
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                path.write_bytes(content)
            except Exception as e:
                raise StorageError(f"Failed to store attachment: {e}") from e
        return str(path.relative_to(self.base_path))
    
    def exists(self, sha256: str) -> bool:
        path = self.base_path / sha256[:2] / sha256[2:4] / sha256
        return path.exists()

storage_backend = AttachmentStorage()

