from policyengine.utils.packages import COUNTRY_PACKAGES
import pytest
from unittest.mock import patch

MOCK_VERSION = "MOCK_VERSION"


@pytest.fixture
def patch_importlib_version():
    def mock_version(package_name):
        if package_name in COUNTRY_PACKAGES:
            return MOCK_VERSION
        else:
            raise Exception(f"Package {package_name} not found")

    with patch(
        "policyengine.utils.packages.version", side_effect=mock_version
    ) as mock:
        yield mock
