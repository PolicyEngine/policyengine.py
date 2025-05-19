from pathlib import Path
import pytest
import tempfile
from unittest.mock import MagicMock, create_autospec, patch
from policyengine.utils.data import CachingGoogleStorageClient
from tests.utils.data.conftest import MockedStorageSupport


class TestCachingGoogleStorageClient:
    @pytest.mark.asyncio
    async def test_when_cache_miss__then_download_file(
        self, mocked_storage: MockedStorageSupport
    ):
        with CachingGoogleStorageClient() as caching_client:
            with tempfile.TemporaryDirectory() as tmpdir:
                mocked_storage.given_stored_data("TEST DATA", "TEST_CRC")
                await caching_client.download(
                    "test_bucket", "blob/path", Path(tmpdir, "output.txt")
                )
                assert (
                    open(Path(tmpdir, "output.txt")).readline() == "TEST DATA"
                )

    @pytest.mark.asyncio
    async def test_when_cache_hit__then_use_cached_value(
        self, mocked_storage: MockedStorageSupport
    ):
        with CachingGoogleStorageClient() as caching_client:
            with tempfile.TemporaryDirectory() as tmpdir:
                mocked_storage.given_stored_data(
                    "INITIAL TEST DATA", "TEST_CRC"
                )
                await caching_client.download(
                    "test_bucket", "blob/path", Path(tmpdir, "output.txt")
                )
                assert (
                    open(Path(tmpdir, "output.txt")).readline()
                    == "INITIAL TEST DATA"
                )

                mocked_storage.given_stored_data(
                    "CRC DID NOT CHANGE SO YOU SHOULD NOT SEE THIS", "TEST_CRC"
                )
                await caching_client.download(
                    "test_bucket", "blob/path", Path(tmpdir, "output.txt")
                )
                assert (
                    open(Path(tmpdir, "output.txt")).readline()
                    == "INITIAL TEST DATA"
                )

    @pytest.mark.asyncio
    async def test_when_crc_updated__then_redownload(
        self, mocked_storage: MockedStorageSupport
    ):
        with CachingGoogleStorageClient() as caching_client:
            with tempfile.TemporaryDirectory() as tmpdir:
                mocked_storage.given_stored_data(
                    "INITIAL TEST DATA", "TEST_CRC"
                )
                await caching_client.download(
                    "test_bucket", "blob/path", Path(tmpdir, "output.txt")
                )
                assert (
                    open(Path(tmpdir, "output.txt")).readline()
                    == "INITIAL TEST DATA"
                )

                mocked_storage.given_stored_data(
                    "UPDATED_TEST_DATA", "UPDATED_TEST_CRC"
                )
                await caching_client.download(
                    "test_bucket", "blob/path", Path(tmpdir, "output.txt")
                )
                assert (
                    open(Path(tmpdir, "output.txt")).readline()
                    == "UPDATED_TEST_DATA"
                )

    @pytest.mark.asyncio
    async def test_when_crc_updated_on_download__then_store_downloaded_crc(
        self, mocked_storage: MockedStorageSupport
    ):
        with CachingGoogleStorageClient() as caching_client:
            with tempfile.TemporaryDirectory() as tmpdir:
                mocked_storage.given_crc_changes_on_download(
                    "FINAL CONTENT", "INITIAL_CRC", "DOWNLOADED_CRC"
                )
                await caching_client.download(
                    "test_bucket", "blob/path", Path(tmpdir, "output.txt")
                )
                assert (
                    open(Path(tmpdir, "output.txt")).readline()
                    == "FINAL CONTENT"
                )

                mocked_storage.given_stored_data(
                    "YOU SHOULD NOT SEE THIS BECAUSE THE CRC IS UNCHANGED FROM DOWNLOADED",
                    "DOWNLOADED_CRC",
                )
                await caching_client.download(
                    "test_bucket", "blob/path", Path(tmpdir, "output.txt")
                )
                assert (
                    open(Path(tmpdir, "output.txt")).readline()
                    == "FINAL CONTENT"
                )
