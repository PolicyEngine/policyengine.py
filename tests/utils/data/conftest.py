import pytest
from unittest.mock import patch

VALID_VERSION = "1.2.3"


class MockedStorageSupport:
    """Test support class for mocking the VersionAwareStorageClient."""

    def __init__(self, mock_storage_client):
        self.mock_storage_client = mock_storage_client

    def given_stored_data(self, data: str, crc: str):
        """Configure the mock to return specific data and CRC."""
        self.mock_storage_client.crc32c.return_value = crc
        self.mock_storage_client.download.return_value = (
            data.encode(),
            crc,
        )
        self.mock_storage_client._get_latest_version.return_value = (
            VALID_VERSION
        )

    def given_crc_changes_on_download(
        self, data: str, initial_crc: str, download_crc: str
    ):
        """Configure the mock where CRC differs between check and download."""
        self.mock_storage_client.crc32c.return_value = initial_crc
        self.mock_storage_client.download.return_value = (
            data.encode(),
            download_crc,
        )
        self.mock_storage_client._get_latest_version.return_value = (
            VALID_VERSION
        )


@pytest.fixture()
def mocked_storage():
    """Fixture that mocks the VersionAwareStorageClient for testing."""
    with patch(
        "policyengine.utils.data.caching_google_storage_client.VersionAwareStorageClient",
        autospec=True,
    ) as mock_class:
        mock_instance = mock_class.return_value
        yield MockedStorageSupport(mock_instance)
