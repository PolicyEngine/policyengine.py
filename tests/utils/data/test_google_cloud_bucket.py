from unittest import TestCase
from unittest.mock import patch
import pytest
from pathlib import Path
from policyengine.utils.google_cloud_bucket import (
    download_file_from_gcs,
    _clear_client,
)


class TestGoogleCloudBucket(TestCase):
    def setUp(self):
        _clear_client()

    @patch(
        "policyengine.utils.google_cloud_bucket.CachingGoogleStorageClient",
        autospec=True,
    )
    def test_download_uses_storage_client(self, client_class):
        client_instance = client_class.return_value
        download_file_from_gcs(
            "TEST_BUCKET", "TEST/FILE/NAME.TXT", "TARGET/PATH"
        )
        client_instance.download.assert_called_with(
            "TEST_BUCKET", "TEST/FILE/NAME.TXT", Path("TARGET/PATH")
        )

    @patch(
        "policyengine.utils.google_cloud_bucket.CachingGoogleStorageClient",
        autospec=True,
    )
    def test_download_only_creates_client_once(self, client_class):
        download_file_from_gcs(
            "TEST_BUCKET", "TEST/FILE/NAME.TXT", "TARGET/PATH"
        )
        download_file_from_gcs(
            "TEST_BUCKET", "TEST/FILE/NAME.TXT", "ANOTHER/PATH"
        )
        client_class.assert_called_once()
