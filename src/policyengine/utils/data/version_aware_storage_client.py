"""GCS client helpers for generation and metadata-versioned objects."""

from __future__ import annotations

import logging
from typing import Optional

from google.cloud.storage import Blob, Bucket, Client

logger = logging.getLogger(__name__)


class VersionAwareStorageClient:
    """Resolve GCS objects by generation, metadata version, or latest object."""

    def __init__(self) -> None:
        self.client = Client()

    def get_blob(
        self,
        bucket_name: str,
        key: str,
        version: Optional[str] = None,
    ) -> Blob:
        bucket = self.client.bucket(bucket_name)

        if version is None:
            logger.debug(
                "No version specified for %s/%s, using latest",
                bucket_name,
                key,
            )
            return bucket.blob(key)

        if version.isdigit():
            try:
                blob = bucket.blob(key, generation=int(version))
                blob.reload()
                logger.info(
                    "Found %s/%s with generation %s",
                    bucket_name,
                    key,
                    version,
                )
                return blob
            except Exception as exc:
                logger.debug(
                    "Generation lookup failed for %s/%s@%s: %s",
                    bucket_name,
                    key,
                    version,
                    exc,
                )

        return self._get_blob_by_metadata_version(bucket, key, version)

    def _get_blob_by_metadata_version(
        self,
        bucket: Bucket,
        key: str,
        version: str,
    ) -> Blob:
        logger.debug(
            "Searching for %s/%s with metadata version %s",
            bucket.name,
            key,
            version,
        )
        matching_blobs = [
            blob
            for blob in bucket.list_blobs(prefix=key, versions=True)
            if blob.name == key
            and blob.metadata is not None
            and blob.metadata.get("version") == version
        ]

        if not matching_blobs:
            raise ValueError(
                f"No blob found with version {version!r} for {bucket.name}/{key}"
            )

        newest_blob = max(matching_blobs, key=lambda blob: blob.generation)
        logger.info(
            "Found %s/%s with metadata version %s and generation %s",
            bucket.name,
            key,
            version,
            newest_blob.generation,
        )
        return newest_blob

    def crc32c(
        self,
        bucket_name: str,
        key: str,
        version: Optional[str] = None,
    ) -> Optional[str]:
        blob = self.get_blob(bucket_name, key, version)
        blob.reload()
        return blob.crc32c

    def download(
        self,
        bucket_name: str,
        key: str,
        version: Optional[str] = None,
    ) -> tuple[bytes, Optional[str]]:
        blob = self.get_blob(bucket_name, key, version)
        content = blob.download_as_bytes()
        return content, blob.crc32c

    def latest_metadata_version(
        self,
        bucket_name: str,
        key: str,
    ) -> Optional[str]:
        blob = self.client.get_bucket(bucket_name).get_blob(key)
        if blob is None:
            logger.warning("No blob found for %s/%s", bucket_name, key)
            return None
        if blob.metadata is None:
            logger.warning("No metadata found for %s/%s", bucket_name, key)
            return None
        version = blob.metadata.get("version")
        if version is None:
            logger.warning("No metadata version found for %s/%s", bucket_name, key)
        return version
