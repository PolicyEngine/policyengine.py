from unittest.mock import patch, call
import pytest
from policyengine.utils.data import SimplifiedGoogleStorageClient

VALID_VERSION = "1.2.3"


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
        mock_instance.bucket.assert_called_with("bucket_name")
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

    @patch(
        "policyengine.utils.data.simplified_google_storage_client.Client",
        autospec=True,
    )
    def test_get_latest_version__returns_version_from_metadata(
        self, mock_client_class
    ):
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.get_bucket.return_value
        blob = bucket.get_blob.return_value

        # Test case where metadata exists with version
        blob.metadata = {"version": VALID_VERSION}

        client = SimplifiedGoogleStorageClient()
        result = client._get_latest_version("test_bucket", "test_key")

        assert result == VALID_VERSION
        mock_instance.get_bucket.assert_called_with("test_bucket")
        bucket.get_blob.assert_called_with("test_key")

    @patch(
        "policyengine.utils.data.simplified_google_storage_client.Client",
        autospec=True,
    )
    def test_get_latest_version__returns_none_when_no_metadata(
        self, mock_client_class
    ):
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.get_bucket.return_value
        blob = bucket.get_blob.return_value

        # Test case where metadata is None
        blob.metadata = None

        client = SimplifiedGoogleStorageClient()
        result = client._get_latest_version("test_bucket", "test_key")

        assert result is None
        mock_instance.get_bucket.assert_called_with("test_bucket")
        bucket.get_blob.assert_called_with("test_key")

    @patch(
        "policyengine.utils.data.simplified_google_storage_client.Client",
        autospec=True,
    )
    def test_get_latest_version__returns_none_when_no_version_in_metadata(
        self, mock_client_class
    ):
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.get_bucket.return_value
        blob = bucket.get_blob.return_value

        # Test case where metadata exists but no version field
        blob.metadata = {"other_field": "value"}

        client = SimplifiedGoogleStorageClient()
        result = client._get_latest_version("test_bucket", "test_key")

        assert result is None
        mock_instance.get_bucket.assert_called_with("test_bucket")
        bucket.get_blob.assert_called_with("test_key")
