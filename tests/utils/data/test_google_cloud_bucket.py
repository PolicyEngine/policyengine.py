from unittest import TestCase
from unittest.mock import patch
import pytest
from pathlib import Path
from policyengine.utils.google_cloud_bucket import (
    download_file_from_gcs,
    _clear_client,
    DATASETS_DIR,
)


class TestGoogleCloudBucket(TestCase):
    def setUp(self):
        _clear_client()

    @patch(
        "policyengine.utils.google_cloud_bucket.CachingGoogleStorageClient",
        autospec=True,
    )
    def test_download_uses_storage_client(self, client_class):
        """Test that download calls the caching client with correct arguments."""
        client_instance = client_class.return_value
        client_instance.download.return_value = "1.0.0"

        local_path, version = download_file_from_gcs(
            "TEST_BUCKET",
            "TEST/FILE/NAME.TXT",
            version=None,
        )

        # Verify the local path is constructed correctly
        expected_local_path = DATASETS_DIR / "TEST/FILE/NAME.TXT"
        assert local_path == str(expected_local_path)

        # Verify the client was called with correct arguments
        client_instance.download.assert_called_with(
            "TEST_BUCKET",
            "TEST/FILE/NAME.TXT",
            expected_local_path,
            version=None,
            return_version=True,
        )

    @patch(
        "policyengine.utils.google_cloud_bucket.CachingGoogleStorageClient",
        autospec=True,
    )
    def test_download_only_creates_client_once(self, client_class):
        """Test that the singleton client is reused across calls."""
        client_instance = client_class.return_value
        client_instance.download.return_value = "1.0.0"

        download_file_from_gcs("TEST_BUCKET", "file1.h5", version=None)
        download_file_from_gcs("TEST_BUCKET", "file2.h5", version=None)
        client_class.assert_called_once()

    @patch(
        "policyengine.utils.google_cloud_bucket.CachingGoogleStorageClient",
        autospec=True,
    )
    def test_download_returns_local_path_and_version(self, client_class):
        """Test that download returns both local path and version."""
        client_instance = client_class.return_value
        client_instance.download.return_value = "2.3.4"

        local_path, version = download_file_from_gcs(
            "my-bucket",
            "states/CA.h5",
            version="2.3.4",
        )

        assert local_path == str(DATASETS_DIR / "states/CA.h5")
        assert version == "2.3.4"

    @patch(
        "policyengine.utils.google_cloud_bucket.CachingGoogleStorageClient",
        autospec=True,
    )
    def test_download_creates_nested_directories(self, client_class):
        """Test that nested GCS keys result in correct local paths."""
        client_instance = client_class.return_value
        client_instance.download.return_value = None

        # Test nested path
        local_path, _ = download_file_from_gcs(
            "bucket", "districts/CA-01.h5", version=None
        )
        assert local_path == str(DATASETS_DIR / "districts/CA-01.h5")

        # Test flat path
        local_path, _ = download_file_from_gcs(
            "bucket", "enhanced_cps_2024.h5", version=None
        )
        assert local_path == str(DATASETS_DIR / "enhanced_cps_2024.h5")
