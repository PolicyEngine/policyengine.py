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
        self, bucket: str, key: str, version: Optional[str] = None
    ) -> Blob:
        """
        Get a versioned blob from the specified bucket and key.
        If version is None, returns the latest version of the blob.
        """
        bucket = self.client.bucket(bucket)
        if version is None:
            return bucket.blob(key)
        else:
            versions: Iterable[Blob] = bucket.list_blobs(
                prefix=key, versions=True
            )
            for v in versions:
                if v.metadata is None:
                    continue  # Skip blobs without metadata
                if v.metadata.get("version") == version:
                    return v
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
        logger.debug(f"Crc is {blob.crc32c}")
        return blob.crc32c

    def download(
        self, bucket: str, key: str, version: Optional[str] = None
    ) -> tuple[bytes, str]:
        """
        get the blob content and associated CRC from google storage.
        """
        logger.info(f"Downloading {bucket}, {key}")
        blob = self.get_versioned_blob(bucket, key, version)

        result = blob.download_as_bytes()
        # According to documentation blob.crc32c is updated as a side effect of
        # downloading the content. As a result this should now be the crc of the downloaded
        # content (i.e. there is not a race condition where it's getting the CRC from the cloud)
        return (result, blob.crc32c)

    def _get_latest_version(self, bucket: str, key: str) -> Optional[str]:
        """
        Get the latest version of a blob in the specified bucket and key.
        If no version is specified, return None.
        """
        blob = self.client.get_bucket(bucket).get_blob(key)
        if blob.metadata is None:
            logging.warning(
                "No metadata found for blob, so it has no version attached."
            )
            return None
        else:
            return blob.metadata.get("version")
