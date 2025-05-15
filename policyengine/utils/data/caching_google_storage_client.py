from contextlib import AbstractContextManager
import diskcache
from pathlib import Path
from policyengine_core.data.dataset import atomic_write
import logging
from .simplified_google_storage_client import SimplifiedGoogleStorageClient

logger = logging.getLogger(__name__)


class CachingGoogleStorageClient(AbstractContextManager):
    """
    Client for downloaded resources from a google storage bucket only when the CRC
    of the blob changes.
    """

    def __init__(self):
        self.client = SimplifiedGoogleStorageClient()
        self.cache = diskcache.Cache()

    def _data_key(self, bucket: str, key: str) -> str:
        return f"{bucket}.{key}.data"

    # To absolutely 100% avoid any possible issue with file corruption or thread contention
    # always replace the current target file with whatever we have cached as an atomic write.
    async def download(self, bucket: str, key: str, target: Path):
        """
        Atomically write the latest version of the cloud storage blob to the target path.
        """
        await self.sync(bucket, key)
        data = self.cache.get(self._data_key(bucket, key))
        if type(data) is bytes:
            logger.debug(
                f"Copying downloaded data for {bucket}, {key} to {target}"
            )
            atomic_write(target, data)
            return
        raise Exception("Expected data for blob to be cached as bytes")

    # If the crc has changed from what we downloaded last time download it again.
    # then update the CRC to whatever we actually downloaded.
    async def sync(self, bucket: str, key: str) -> None:
        """
        Cache the resource if the CRC has changed.
        """
        logger.info(f"Syncing {bucket}, {key} to cache")
        datakey = f"{bucket}.{key}.data"
        crckey = f"{bucket}.{key}.crc"

        crc = self.client.crc32c(bucket, key)
        if crc is None:
            raise Exception(f"Unable to find {key} in bucket {bucket}")

        prev_crc = self.cache.get(crckey, default=None)
        logger.debug(f"Previous crc for {bucket}, {key} was {prev_crc}")
        if prev_crc == crc:
            logger.info(
                f"Cache exists and crc is unchanged for {bucket}, {key}."
            )
            return

        [content, downloaded_crc] = await self.client.download(bucket, key)
        logger.info(
            f"Downloaded new version of {bucket}, {key} with crc {downloaded_crc}"
        )

        # atomic transaction to update both the data and the metadata
        # at the same time.
        with self.cache as c:
            logger.debug(f"Updating cache...")
            self.cache.set(datakey, content)
            # Whatever the CRC was before we downloaded, we set the cache CRC
            # to the CRC reported by the download itself to avoid race conditions.
            self.cache.set(crckey, downloaded_crc)

    def clear(self):
        self.cache.clear()

    def __enter__(self) -> "CachingGoogleStorageClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Raise any exception triggered within the runtime context."""
        self.clear()
        return None
