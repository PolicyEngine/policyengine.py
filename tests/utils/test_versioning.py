import pytest
from policyengine.utils.versioning import (
    get_version,
    get_country_package_version,
)
from tests.fixtures.utils.versioning import patch_importlib_version
from importlib.metadata import PackageNotFoundError


class TestGetVersion:
    def test__given_package_exist__then_return_version(
        self, patch_importlib_version
    ):
        test_package = "policyengine_us"

        test_version = get_version(test_package)

        # Version number defined by mock
        assert test_version == "1.0.0"

    def test__given_package_does_not_exist__then_raise_exception(
        self, patch_importlib_version
    ):
        test_package = "non_existent_package"

        with pytest.raises(
            RuntimeError,
            match=f"Could not get version for package {test_package}",
        ):
            get_version(test_package)


class TestGetCountryPackageVersion:
    def test__given_country_package_exists__then_return_version(
        self, patch_importlib_version
    ):
        test_country = "us"

        test_version = get_country_package_version(test_country)

        # Version number defined by mock
        assert test_version == "1.0.0"

    def test__given_country_package_does_not_exist__then_raise_exception(
        self, patch_importlib_version
    ):
        test_country = "non_existent_country"

        with pytest.raises(
            ValueError, match=f"Country ID {test_country} is not recognized."
        ):
            get_country_package_version(test_country)

    def test__given_country_not_supported__then_raise_error(
        self, patch_importlib_version
    ):
        unsupported_country = "ca"

        with pytest.raises(
            ValueError,
            match=f"Country ID {unsupported_country} is not supported.",
        ):
            get_country_package_version(unsupported_country)
