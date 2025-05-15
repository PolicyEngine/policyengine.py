import asyncio
from policyengine_core.data.dataset import atomic_write
import logging
from google.cloud.storage import Client

logger = logging.getLogger(__name__)


class SimplifiedGoogleStorageClient:
    """
    Class separating out just the interactions with google storage required to
    cache downloaded files.

    Simplifies the dependent code and unit testing.
    """

    def __init__(self):
        self.client = Client()

    def crc32c(self, bucket: str, key: str) -> str | None:
        """
        get the current CRC of the specified blob. None if it doesn't exist.
        """
        logger.debug(f"Getting crc for {bucket}, {key}")
        blob = self.client.bucket(bucket).blob(key)
        blob.reload()
        logger.debug(f"Crc is {blob.crc32c}")
        return blob.crc32c

    async def download(self, bucket: str, key: str) -> tuple[bytes, str]:
        """
        get the blob content and associated CRC from google storage.
        """
        logger.debug(f"Downloading {bucket}, {key}")
        blob = self.client.bucket(bucket).blob(key)

        # async implmentation as per https://github.com/googleapis/python-storage/blob/main/samples/snippets/storage_async_download.py
        def download():
            return blob.download_as_bytes()

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, download)
        # According to documentation blob.crc32c is updated as a side effect of
        # downloading the content. As a result this should now be the crc of the downloaded
        # content (i.e. there is not a race condition where it's getting the CRC from the cloud)
        return (result, blob.crc32c)
