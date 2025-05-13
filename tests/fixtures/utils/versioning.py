from policyengine.constants import SUPPORTED_COUNTRY_PACKAGES
from importlib.metadata import PackageNotFoundError
import pytest
from unittest.mock import patch


@pytest.fixture
def patch_importlib_version():
    def mock_version(package_name):
        if package_name in SUPPORTED_COUNTRY_PACKAGES:
            return "1.0.0"
        else:
            raise Exception(f"Package {package_name} not found")

    with patch(
        "policyengine.utils.versioning.version", side_effect=mock_version
    ) as mock:
        yield mock
