from __future__ import annotations

from pathlib import Path

from app.services.storage.base import ReportObjectNotFoundError, ReportStorage, ReportStorageError


class LocalFilesystemReportStorage(ReportStorage):
    """Yalnızca yerel geliştirme için dosya sistemi tabanlı depolama.
    """

    def __init__(self, base_dir: str):
        self._base_dir = Path(base_dir).resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, object_key: str) -> Path:
        candidate = (self._base_dir / object_key).resolve()
        if self._base_dir not in candidate.parents and candidate != self._base_dir:
            raise ReportStorageError(f"Geçersiz object_key (path traversal şüphesi): {object_key}")
        return candidate

    def upload(self, object_key: str, content: bytes, content_type: str) -> None:
        path = self._resolve(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def download(self, object_key: str) -> bytes:
        path = self._resolve(object_key)
        if not path.is_file():
            raise ReportObjectNotFoundError(f"Yerel rapor dosyası bulunamadı: {object_key}")
        return path.read_bytes()

    def exists(self, object_key: str) -> bool:
        return self._resolve(object_key).is_file()
