import pytest
from policyengine.utils.versioning import (
    get_country_package_version,
)
from tests.fixtures.utils.versioning import (
    patch_importlib_version,
    MOCK_VERSION,
)
from importlib.metadata import PackageNotFoundError


class TestGetCountryPackageVersion:
    def test__given_package_exists__then_return_version(
        self, patch_importlib_version
    ):
        test_country = "us"

        test_version = get_country_package_version(test_country)

        # Version number defined by mock
        assert test_version == MOCK_VERSION

    def test__given_package_does_not_exist__then_raise_exception(
        self, patch_importlib_version
    ):
        test_country = "zz"

        with pytest.raises(
            Exception,
            match=f"Package policyengine_{test_country} not found",
        ):
            get_country_package_version(test_country)
