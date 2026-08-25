from abc import ABC, abstractmethod


class ReportStorageError(Exception):
    pass


class ReportObjectNotFoundError(ReportStorageError):
    pass


class ReportStorage(ABC):

    @abstractmethod
    def upload(self, object_key: str, content: bytes, content_type: str) -> None: ...

    @abstractmethod
    def download(self, object_key: str) -> bytes: ...

    @abstractmethod
    def exists(self, object_key: str) -> bool: ...
