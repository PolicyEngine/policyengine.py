import pytest
from unittest.mock import patch

VALID_VERSION = "1.2.3"


class MockedStorageSupport:
    def __init__(self, mock_simple_storage_client):
        self.mock_simple_storage_client = mock_simple_storage_client

    def given_stored_data(self, data: str, crc: str):
        self.mock_simple_storage_client.crc32c.return_value = crc
        self.mock_simple_storage_client.download.return_value = (
            data.encode(),
            crc,
        )
        self.mock_simple_storage_client._get_latest_version.return_value = (
            VALID_VERSION
        )

    def given_crc_changes_on_download(
        self, data: str, initial_crc: str, download_crc: str
    ):
        self.mock_simple_storage_client.crc32c.return_value = initial_crc
        self.mock_simple_storage_client.download.return_value = (
            data.encode(),
            download_crc,
        )
        self.mock_simple_storage_client._get_latest_version.return_value = (
            VALID_VERSION
        )


@pytest.fixture()
def mocked_storage():
    with patch(
        "policyengine.utils.data.caching_google_storage_client.SimplifiedGoogleStorageClient",
        autospec=True,
    ) as mock_class:
        mock_instance = mock_class.return_value
        yield MockedStorageSupport(mock_instance)
