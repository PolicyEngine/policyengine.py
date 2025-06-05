import asyncio
from policyengine_core.data.dataset import atomic_write
import logging
from google.cloud.storage import Client, Blob
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


class SimplifiedGoogleStorageClient:
    """
    Class separating out just the interactions with google storage required to
    cache downloaded files.

    Simplifies the dependent code and unit testing.
    """

    def __init__(self):
        self.client = Client()

    def get_versioned_blob(
        self, bucket_name: str, key: str, version: Optional[str] = None
    ) -> Blob:
        """
        Get a versioned blob from the specified bucket and key.
        If version is None, returns the latest version of the blob.
        """
        bucket = self.client.bucket(bucket_name)
        if version is None:
            return bucket.blob(key)
        logging.debug(
            "Searching {bucket_name}, {prefix}* for version {version}"
        )
        versions: Iterable[Blob] = bucket.list_blobs(prefix=key, versions=True)
        for v in versions:
            if v.metadata is None:
                continue  # Skip blobs without metadata
            if v.metadata.get("version") == version:
                logging.info(
                    f"Blob {bucket_name}, {v.path} has version {version}"
                )
                return v
        logging.info(f"No version {version} found for {bucket_name}, {key}")
        raise ValueError(
            f"Could not find version {version} of blob {key} in bucket {bucket.name}"
        )

    def crc32c(
        self, bucket_name: str, key: str, version: Optional[str] = None
    ) -> Optional[str]:
        """
        get the current CRC of the specified blob. None if it doesn't exist.
        """
        logger.debug(f"Getting crc for {bucket_name}, {key}")
        blob = self.get_versioned_blob(bucket_name, key, version)

        blob.reload()
        logger.info(f"Crc for {bucket_name}, {key} is {blob.crc32c}")
        return blob.crc32c

    def download(
        self, bucket: str, key: str, version: Optional[str] = None
    ) -> tuple[bytes, str]:
        """
        get the blob content and associated CRC from google storage.
        """
        logger.debug(
            f"Downloading {bucket}, {key}{ ', version:' + version if version is not None else ''}"
        )
        blob = self.get_versioned_blob(bucket, key, version)

        result = blob.download_as_bytes()
        logger.info(
            f"Downloaded {bucket}, {key}{ ', version:' + version if version is not None else ''}"
        )
        # According to documentation blob.crc32c is updated as a side effect of
        # downloading the content. As a result this should now be the crc of the downloaded
        # content (i.e. there is not a race condition where it's getting the CRC from the cloud)
        return (result, blob.crc32c)

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
