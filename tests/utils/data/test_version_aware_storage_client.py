"""Tests for VersionAwareStorageClient."""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest
from policyengine.utils.data import VersionAwareStorageClient

VALID_VERSION = "1.2.3"


class TestVersionAwareStorageClient:
    """Tests for VersionAwareStorageClient."""

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_crc32c__gets_crc(self, mock_client_class):
        """Test that crc32c returns the blob's CRC."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.bucket.return_value
        blob = bucket.blob.return_value

        blob.crc32c = "TEST_CRC"

        client = VersionAwareStorageClient()
        assert client.crc32c("bucket_name", "content.txt") == "TEST_CRC"
        mock_instance.bucket.assert_called_with("bucket_name")
        bucket.blob.assert_called_with("content.txt")
        blob.reload.assert_called()

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_download__downloads_content(self, mock_client_class):
        """Test that download returns content and CRC."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.bucket.return_value
        blob = bucket.blob.return_value

        blob.download_as_bytes.return_value = "hello, world".encode()
        blob.crc32c = "TEST_CRC"

        client = VersionAwareStorageClient()
        data, crc = client.download("bucket", "blob.txt")
        assert data == "hello, world".encode()
        assert crc == "TEST_CRC"

        mock_instance.bucket.assert_called_with("bucket")
        bucket.blob.assert_called_with("blob.txt")

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_get_latest_version__returns_version_from_metadata(
        self, mock_client_class
    ):
        """Test that _get_latest_version returns the version from blob metadata."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.get_bucket.return_value
        blob = bucket.get_blob.return_value

        blob.metadata = {"version": VALID_VERSION}

        client = VersionAwareStorageClient()
        result = client._get_latest_version("test_bucket", "test_key")

        assert result == VALID_VERSION
        mock_instance.get_bucket.assert_called_with("test_bucket")
        bucket.get_blob.assert_called_with("test_key")

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_get_latest_version__returns_none_when_no_metadata(
        self, mock_client_class
    ):
        """Test that _get_latest_version returns None when blob has no metadata."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.get_bucket.return_value
        blob = bucket.get_blob.return_value

        blob.metadata = None

        client = VersionAwareStorageClient()
        result = client._get_latest_version("test_bucket", "test_key")

        assert result is None
        mock_instance.get_bucket.assert_called_with("test_bucket")
        bucket.get_blob.assert_called_with("test_key")

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_get_latest_version__returns_none_when_no_version_in_metadata(
        self, mock_client_class
    ):
        """Test that _get_latest_version returns None when metadata has no version field."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.get_bucket.return_value
        blob = bucket.get_blob.return_value

        blob.metadata = {"other_field": "value"}

        client = VersionAwareStorageClient()
        result = client._get_latest_version("test_bucket", "test_key")

        assert result is None
        mock_instance.get_bucket.assert_called_with("test_bucket")
        bucket.get_blob.assert_called_with("test_key")

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_get_blob__no_version_returns_latest(self, mock_client_class):
        """Test that get_blob with no version returns the latest blob."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.bucket.return_value
        expected_blob = bucket.blob.return_value

        client = VersionAwareStorageClient()
        result = client.get_blob("test_bucket", "test_key")

        assert result == expected_blob
        mock_instance.bucket.assert_called_with("test_bucket")
        bucket.blob.assert_called_with("test_key")

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_get_blob__generation_version_uses_generation(
        self, mock_client_class
    ):
        """Test that numeric version strings are treated as GCS generations."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.bucket.return_value
        expected_blob = bucket.blob.return_value

        client = VersionAwareStorageClient()
        result = client.get_blob(
            "test_bucket", "test_key", version="1234567890"
        )

        assert result == expected_blob
        mock_instance.bucket.assert_called_with("test_bucket")
        bucket.blob.assert_called_with("test_key", generation=1234567890)

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_get_blob__metadata_version_searches_blobs(
        self, mock_client_class
    ):
        """Test that semantic version strings search blob metadata."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.bucket.return_value

        # Create mock blobs with different metadata versions
        blob1 = MagicMock()
        blob1.metadata = {"version": "1.0.0"}
        blob2 = MagicMock()
        blob2.metadata = {"version": "1.2.3"}
        blob3 = MagicMock()
        blob3.metadata = None

        bucket.list_blobs.return_value = [blob1, blob3, blob2]

        client = VersionAwareStorageClient()
        result = client.get_blob("test_bucket", "test_key", version="1.2.3")

        assert result == blob2
        bucket.list_blobs.assert_called_with(prefix="test_key", versions=True)

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_get_blob__metadata_version_not_found_raises(
        self, mock_client_class
    ):
        """Test that missing metadata version raises ValueError."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.bucket.return_value

        blob1 = MagicMock()
        blob1.metadata = {"version": "1.0.0"}

        bucket.list_blobs.return_value = [blob1]

        client = VersionAwareStorageClient()
        with pytest.raises(ValueError) as exc_info:
            client.get_blob("test_bucket", "test_key", version="2.0.0")

        assert "No blob found with version '2.0.0'" in str(exc_info.value)

    @patch(
        "policyengine.utils.data.version_aware_storage_client.Client",
        autospec=True,
    )
    def test_get_blob__generation_fallback_to_metadata(
        self, mock_client_class
    ):
        """Test that generation lookup falls back to metadata if reload fails."""
        mock_instance = mock_client_class.return_value
        bucket = mock_instance.bucket.return_value

        # Make generation-based lookup fail
        generation_blob = bucket.blob.return_value
        generation_blob.reload.side_effect = Exception("Generation not found")

        # Set up metadata-based lookup to succeed
        metadata_blob = MagicMock()
        metadata_blob.metadata = {"version": "999"}
        bucket.list_blobs.return_value = [metadata_blob]

        client = VersionAwareStorageClient()
        # "999" looks like a number, so it tries generation first, then falls back
        result = client.get_blob("test_bucket", "test_key", version="999")

        assert result == metadata_blob
        bucket.list_blobs.assert_called_with(prefix="test_key", versions=True)
