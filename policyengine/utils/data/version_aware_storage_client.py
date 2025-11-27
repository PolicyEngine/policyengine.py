"""
GCS client supporting multiple versioning strategies.

This module provides a unified interface for downloading versioned blobs from
Google Cloud Storage, supporting both:
1. Generation-based versioning (GCS native object generations)
2. Metadata-based versioning (version string in blob metadata)
"""

import logging
from typing import Optional

from google.cloud.storage import Blob, Bucket, Client

logger = logging.getLogger(__name__)


class VersionAwareStorageClient:
    """
    GCS client supporting multiple versioning strategies.

    Versioning strategies:
    1. Generation-based: version is a GCS generation number (integer string)
    2. Metadata-based: version is stored in blob.metadata["version"]
    3. None: get the latest blob

    The client attempts to resolve versions in this order:
    - If version looks like an integer, try generation-based first
    - Fall back to metadata-based matching
    - Raise an error if no matching version is found
    """

    def __init__(self):
        self.client = Client()

    def get_blob(
        self,
        bucket_name: str,
        key: str,
        version: Optional[str] = None,
    ) -> Blob:
        """
        Get a blob, resolving version using the appropriate strategy.

        Args:
            bucket_name: The GCS bucket name.
            key: The blob path within the bucket.
            version: Optional version string. Can be:
                - None: get latest blob
                - Integer string: treated as GCS generation number
                - Other string: matched against blob metadata["version"]

        Returns:
            The resolved Blob object.

        Raises:
            ValueError: If a specific version is requested but not found.
        """
        bucket = self.client.bucket(bucket_name)

        if version is None:
            # No version specified: return latest
            logger.debug(
                f"No version specified for {bucket_name}/{key}, using latest"
            )
            return bucket.blob(key)

        # Try generation-based first (if version looks like an integer)
        if version.isdigit():
            logger.debug(
                f"Version '{version}' looks like a generation number, "
                f"trying generation-based lookup for {bucket_name}/{key}"
            )
            try:
                blob = bucket.blob(key, generation=int(version))
                # Verify the blob exists by reloading it
                blob.reload()
                logger.info(
                    f"Found blob {bucket_name}/{key} with generation {version}"
                )
                return blob
            except Exception as e:
                logger.debug(
                    f"Generation-based lookup failed for {bucket_name}/{key}@{version}: {e}. "
                    f"Falling back to metadata-based lookup."
                )

        # Metadata-based: iterate versions and match
        return self._get_blob_by_metadata_version(bucket, key, version)

    def _get_blob_by_metadata_version(
        self,
        bucket: Bucket,
        key: str,
        version: str,
    ) -> Blob:
        """
        Find a blob whose metadata["version"] matches the requested version.

        Args:
            bucket: The GCS Bucket object.
            key: The blob path within the bucket.
            version: The version string to match in metadata.

        Returns:
            The matching Blob object.

        Raises:
            ValueError: If no blob with the matching version is found.
        """
        logger.debug(
            f"Searching for blob {bucket.name}/{key} with metadata version '{version}'"
        )
        versions = bucket.list_blobs(prefix=key, versions=True)
        for blob in versions:
            if blob.metadata and blob.metadata.get("version") == version:
                logger.info(
                    f"Found blob {bucket.name}/{key} with metadata version '{version}'"
                )
                return blob

        raise ValueError(
            f"No blob found with version '{version}' for {bucket.name}/{key}"
        )

    def crc32c(
        self,
        bucket_name: str,
        key: str,
        version: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get the CRC32C checksum for a blob.

        Args:
            bucket_name: The GCS bucket name.
            key: The blob path within the bucket.
            version: Optional version string.

        Returns:
            The CRC32C checksum string, or None if blob doesn't exist.
        """
        logger.debug(f"Getting CRC32C for {bucket_name}/{key}")
        blob = self.get_blob(bucket_name, key, version)
        blob.reload()
        logger.info(f"CRC32C for {bucket_name}/{key} is {blob.crc32c}")
        return blob.crc32c

    def download(
        self,
        bucket_name: str,
        key: str,
        version: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """
        Download blob content and return (content, crc).

        Args:
            bucket_name: The GCS bucket name.
            key: The blob path within the bucket.
            version: Optional version string.

        Returns:
            A tuple of (content_bytes, crc32c_checksum).
        """
        logger.debug(
            f"Downloading {bucket_name}/{key}"
            f"{', version: ' + version if version else ''}"
        )
        blob = self.get_blob(bucket_name, key, version)
        content = blob.download_as_bytes()
        logger.info(
            f"Downloaded {bucket_name}/{key}"
            f"{', version: ' + version if version else ''}"
        )
        # According to documentation, blob.crc32c is updated as a side effect of
        # downloading the content. This should be the CRC of the downloaded
        # content (avoiding race conditions with the cloud).
        return (content, blob.crc32c)

    def _get_latest_version(self, bucket: str, key: str) -> Optional[str]:
        """
        Get the latest version of a blob in the specified bucket and key.
        If no version is specified, return None.
        """
        logger.debug(f"Getting latest version of {bucket}, {key}")
        blob = self.client.get_bucket(bucket).get_blob(key)
        if blob is None:
            logging.warning(f"No blob found in bucket {bucket} with key {key}")
            return None

        if blob.metadata is None:
            logging.warning(
                f"No metadata found for blob {bucket}, {key}, so it has no version attached."
            )
            return None

        version = blob.metadata.get("version")
        if version is None:
            logging.warning(
                f"Blob {bucket}, {key} does not have a version in its metadata"
            )
            return None
        logging.info(
            f"Metadata for blob {bucket}, {key} has version: {version}"
        )
        return blob.metadata.get("version")
