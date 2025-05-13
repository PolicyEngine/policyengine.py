import pytest
from policyengine.utils.packages import (
    get_country_package_name,
    get_country_package_version,
)
from tests.fixtures.utils.packages import (
    patch_importlib_version,
    MOCK_VERSION,
)


class TestGetCountryPackageName:
    def test__given_country_id__then_return_package_name(self):
        test_country = "us"

        test_package_name = get_country_package_name(test_country)

        assert test_package_name == "policyengine_us"

    def test__given_non_standard_country_id__then_return_package_name(self):
        test_country = "ca"

        test_package_name = get_country_package_name(test_country)

        assert test_package_name == "policyengine_canada"

    def test__given_unsupported_country_id__then_return_package_name(self):
        test_country = "zz"

        with pytest.raises(Exception, match="Unsupported country ID: zz"):
            get_country_package_name(test_country)


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
            match=f"Unsupported country ID: {test_country}. Supported IDs are: ",
        ):
            get_country_package_version(test_country)
