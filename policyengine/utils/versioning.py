from importlib.metadata import version
from policyengine.constants import (
    SUPPORTED_COUNTRY_IDS,
    UNSUPPORTED_COUNTRY_IDS,
)


def get_version(package: str) -> str:
    try:
        return version(package)
    except Exception as e:
        raise RuntimeError(
            f"Could not get version for package {package}: {e}"
        ) from e


def get_country_package_version(country_id: str) -> str:

    if country_id in UNSUPPORTED_COUNTRY_IDS:
        raise ValueError(f"Country ID {country_id} is not supported.")

    if country_id not in SUPPORTED_COUNTRY_IDS:
        raise ValueError(f"Country ID {country_id} is not recognized.")

    try:
        return version(f"policyengine_{country_id}")
    except Exception as e:
        raise RuntimeError(
            f"Could not get version for package policyengine_{country_id}: {e}"
        ) from e
