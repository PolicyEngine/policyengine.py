from importlib.metadata import version
from policyengine.constants import (
    SUPPORTED_COUNTRY_IDS,
    UNSUPPORTED_COUNTRY_IDS,
)


def get_country_package_version(country_id: str) -> str:

    # Canada package doesn't use two-letter country code
    if country_id == "ca":
        country_id = "canada"

    return version(f"policyengine_{country_id}")
