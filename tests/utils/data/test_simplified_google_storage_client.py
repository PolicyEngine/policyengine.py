from unittest.mock import patch, call
import pytest
from policyengine.utils.data import SimplifiedGoogleStorageClient


class TestSimplifiedGoogleStorageClient:
    @patch(
        "policyengine.utils.data.simplified_google_storage_client.Client",
        autospec=True,
    )
    def test_crc32c__gets_crc(self, mock_client_class):
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.bucket.return_value
        blob = bucket.blob.return_value

        blob.crc32c = "TEST_CRC"

        client = SimplifiedGoogleStorageClient()
        assert client.crc32c("bucket_name", "content.txt") == "TEST_CRC"
        assert (
            mock_instance.bucket.call_count >= 1
        )  # There is a second call in get_versioned_blob
        first_call = mock_instance.bucket.call_args_list[0]
        assert first_call == call("bucket_name")
        bucket.blob.assert_called_with("content.txt")
        blob.reload.assert_called()

    @patch(
        "policyengine.utils.data.simplified_google_storage_client.Client",
        autospec=True,
    )
    def test_download__downloads_content(self, mock_client_class):
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.bucket.return_value
        blob = bucket.blob.return_value

        blob.download_as_bytes.return_value = "hello, world".encode()
        blob.crc32c = "TEST_CRC"

        client = SimplifiedGoogleStorageClient()
        [data, crc] = client.download("bucket", "blob.txt")
        assert data == "hello, world".encode()
        assert crc == "TEST_CRC"

        mock_instance.bucket.assert_called_with("bucket")
        bucket.blob.assert_called_with("blob.txt")
