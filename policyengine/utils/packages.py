from importlib.metadata import version


def get_country_package_name(country_id: str) -> str:
    if country_id in NON_STANDARD_COUNTRY_CODES:
        return f"policyengine_{NON_STANDARD_COUNTRY_CODES[country_id]}"
    if country_id in COUNTRY_IDS:
        return f"policyengine_{country_id}"
    raise ValueError(
        f"Unsupported country ID: {country_id}. Supported IDs are: {COUNTRY_IDS}"
    )


def get_country_package_version(country_id: str) -> str:

    package_name = get_country_package_name(country_id)
    return version(package_name)


COUNTRY_IDS = ["us", "uk", "ca", "il", "ng"]

NON_STANDARD_COUNTRY_CODES = {
    "ca": "canada",
}

COUNTRY_PACKAGES = [
    get_country_package_name(country) for country in COUNTRY_IDS
]
