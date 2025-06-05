from contextlib import AbstractContextManager
import diskcache
from pathlib import Path
from policyengine_core.data.dataset import atomic_write
import logging
from .simplified_google_storage_client import SimplifiedGoogleStorageClient
from typing import Optional

logger = logging.getLogger(__name__)


class CachingGoogleStorageClient(AbstractContextManager):
    """
    Client for downloaded resources from a google storage bucket only when the CRC
    of the blob changes.
    """

    def __init__(self):
        self.client = SimplifiedGoogleStorageClient()
        self.cache = diskcache.Cache()

    def _data_key(
        self, bucket: str, key: str, version: Optional[str] = None
    ) -> str:
        return f"{bucket}.{key}.{version}.data"

    # To absolutely 100% avoid any possible issue with file corruption or thread contention
    # always replace the current target file with whatever we have cached as an atomic write.
    def download(
        self,
        bucket: str,
        key: str,
        target: Path,
        version: Optional[str] = None,
        return_version: bool = False,
    ):
        """
        Atomically write the latest version of the cloud storage blob to the target path.
        """
        if version is None:
            # If no version is specified, get the latest version from the cache
            version = self.client._get_latest_version(bucket, key)
            logging.warning(
                f"No version specified for {bucket}, {key}. Using latest version: {version}"
            )
        self.sync(bucket, key, version)
        data = self.cache.get(self._data_key(bucket, key, version))
        if type(data) is bytes:
            logger.info(
                f"Copying downloaded data for {bucket}, {key} to {target}"
            )
            atomic_write(target, data)
            logger.info(
                f"Data successfully copied to {target} with version {version}"
            )
            if return_version:
                return version
            return
        logger.error(
            f"Cached data for {bucket}, {key}{', ' + version if version is not None else ''} is not bytes."
        )
        raise Exception("Expected data for blob to be cached as bytes")

    # If the crc has changed from what we downloaded last time download it again.
    # then update the CRC to whatever we actually downloaded.
    def sync(
        self, bucket: str, key: str, version: Optional[str] = None
    ) -> None:
        """
        Cache the resource if the CRC has changed.
        """
        logger.info(f"Syncing {bucket}, {key}, {version} to cache")
        datakey = f"{bucket}.{key}.{version}.data"
        crckey = f"{bucket}.{key}.{version}.crc"

        crc = self.client.crc32c(bucket, key, version=version)
        id_string = (
            f"{bucket}, {key}{', ' + version if version is not None else ''}"
        )
        if crc is None:
            raise Exception(f"Unable to find {id_string}")

        prev_crc = self.cache.get(crckey, default=None)
        logger.debug(f"Previous crc for {id_string} was {prev_crc}")
        if prev_crc == crc:
            logger.info(f"Cache exists and crc is unchanged for {id_string} .")
            return
        [content, downloaded_crc] = self.client.download(
            bucket, key, version=version
        )
        logger.info(
            f"Downloaded new version of {id_string} with crc {downloaded_crc}"
        )

        # atomic transaction to update both the data and the metadata
        # at the same time.
        with self.cache as c:
            logger.debug(f"Updating cache...")
            self.cache.set(datakey, content)
            # Whatever the CRC was before we downloaded, we set the cache CRC
            # to the CRC reported by the download itself to avoid race conditions.
            self.cache.set(crckey, downloaded_crc)
        logger.info("Cache updated for {id_string}")

    def clear(self):
        self.cache.clear()

    def __enter__(self) -> "CachingGoogleStorageClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Raise any exception triggered within the runtime context."""
        self.clear()
        return None
