"""Disk-cached Google Cloud Storage downloads."""

from __future__ import annotations

import logging
import os
import tempfile
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Optional

import diskcache

from .version_aware_storage_client import VersionAwareStorageClient

logger = logging.getLogger(__name__)


def _atomic_write(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
        os.replace(temp_path, target)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


class CachingGoogleStorageClient(AbstractContextManager):
    """Download GCS objects through a CRC-keyed disk cache."""

    def __init__(self) -> None:
        self.client = VersionAwareStorageClient()
        self.cache = diskcache.Cache()

    @staticmethod
    def _data_key(bucket: str, key: str, version: Optional[str] = None) -> str:
        return f"{bucket}.{key}.{version}.data"

    @staticmethod
    def _crc_key(bucket: str, key: str, version: Optional[str] = None) -> str:
        return f"{bucket}.{key}.{version}.crc"

    def download(
        self,
        bucket: str,
        key: str,
        target: Path,
        version: Optional[str] = None,
        return_version: bool = False,
    ) -> Optional[str]:
        if version is None:
            version = self.client.latest_metadata_version(bucket, key)
            logger.warning(
                "No version specified for %s/%s; using latest metadata version %s",
                bucket,
                key,
                version,
            )

        self.sync(bucket, key, version)
        data = self.cache.get(self._data_key(bucket, key, version))
        if isinstance(data, bytes):
            _atomic_write(target, data)
            return version if return_version else None

        raise TypeError(
            f"Expected cached data for {bucket}/{key}@{version} to be bytes"
        )

    def sync(
        self,
        bucket: str,
        key: str,
        version: Optional[str] = None,
    ) -> None:
        crc = self.client.crc32c(bucket, key, version=version)
        if crc is None:
            raise FileNotFoundError(f"Unable to find gs://{bucket}/{key}")

        data_key = self._data_key(bucket, key, version)
        crc_key = self._crc_key(bucket, key, version)
        if self.cache.get(crc_key, default=None) == crc:
            return

        content, downloaded_crc = self.client.download(bucket, key, version=version)
        with self.cache as cache:
            cache.set(data_key, content)
            cache.set(crc_key, downloaded_crc)

    def clear(self) -> None:
        self.cache.clear()

    def __enter__(self) -> CachingGoogleStorageClient:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.clear()
        return None
