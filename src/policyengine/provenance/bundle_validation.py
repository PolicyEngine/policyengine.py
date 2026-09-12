"""Validate independently pinned measurement configuration in bundle manifests."""

import re
from datetime import date
from typing import Any, Mapping
from urllib.parse import urlparse

# Canonical PEP 440 spellings only: no aliases, leading zeroes, or implicit
# pre/post/dev numbers. Keep bootstrap validation independent of packaging.
_INTEGER = r"(?:0|[1-9][0-9]*)"
_NORMALIZED_VERSION = re.compile(
    rf"(?:[1-9][0-9]*!)?{_INTEGER}(?:\.{_INTEGER})*"
    rf"(?:(?:a|b|rc){_INTEGER})?(?:\.post{_INTEGER})?(?:\.dev{_INTEGER})?"
    r"(?:\+[a-z0-9]+(?:\.[a-z0-9]+)*)?"
)


def _is_normalized_version(value: Any) -> bool:
    if not isinstance(value, str) or not _NORMALIZED_VERSION.fullmatch(value):
        return False
    local = value.partition("+")[2]
    return all(
        not part.isdigit() or part == str(int(part)) for part in local.split(".")
    )


def validate_spm_configuration(configuration: Any) -> None:
    """Validate JSON defaults using only the standard library.

    Both runtime loading and pre-install bundle maintenance call this function.
    Keep it importable by file path without executing the wrapper package.
    """
    if not isinstance(configuration, Mapping):
        raise ValueError("SPM measurement configuration must be an object")
    allowed = {
        "forecast_content_sha256",
        "scenario",
        "geography_kind",
        "geography_id",
        "county_vintage",
        "as_of",
    }
    if set(configuration) - allowed:
        raise ValueError("SPM measurement configuration contains unknown fields")
    sha256 = configuration.get("forecast_content_sha256")
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("SPM forecast_content_sha256 must be a lowercase SHA256")
    scenario = configuration.get("scenario")
    if not isinstance(scenario, str) or not re.fullmatch(r"\S+", scenario):
        raise ValueError("SPM scenario must be nonempty without whitespace")
    kind = configuration.get("geography_kind", "county")
    if kind not in ("county", "metro", "national"):
        raise ValueError("SPM geography_kind must be county, metro, or national")
    geography_id = configuration.get("geography_id")
    if geography_id is not None and (
        not isinstance(geography_id, str)
        or not geography_id.strip()
        or geography_id != geography_id.strip()
    ):
        raise ValueError("SPM geography_id must be nonempty without outer whitespace")
    if (kind == "metro") != (geography_id is not None):
        raise ValueError("Only metro SPM selection requires geography_id")
    vintage = configuration.get("county_vintage", "2020")
    if not isinstance(vintage, str) or not re.fullmatch(r"[0-9]{4}", vintage):
        raise ValueError("SPM county_vintage must be a four-digit year")
    as_of = configuration.get("as_of")
    if as_of is not None:
        if not isinstance(as_of, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}", as_of
        ):
            raise ValueError("SPM as_of must be an ISO YYYY-MM-DD date")
        if date.fromisoformat(as_of).isoformat() != as_of:
            raise ValueError("SPM as_of must be an ISO YYYY-MM-DD date")


def validate_bundle_measurements(
    bundle: Mapping[str, Any], *, require_published_spm: bool = False
) -> None:
    """Reject malformed SPM pins, retaining support for historical bundles.

    Drafts may stage a content pin before registry publication. The stricter
    measurement-pin check requires the calculator's published wheel identity as
    well. It does not establish country/data compatibility or release readiness.
    """
    measurements = bundle.get("measurements", {})
    if not isinstance(measurements, Mapping):
        raise ValueError("Bundle measurements must be an object")
    if "spm" not in measurements:
        if require_published_spm:
            raise ValueError("Published SPM pin check requires measurements.spm")
        return
    validate_spm_configuration(measurements["spm"])
    packages = bundle.get("packages", {})
    if not isinstance(packages, Mapping):
        raise ValueError("Bundle packages must be an object")
    calculator = packages.get("spm-calculator")
    if calculator is None:
        if require_published_spm:
            raise ValueError("SPM promotion pending: no published spm-calculator pin")
        return
    if not isinstance(calculator, Mapping):
        raise ValueError("spm-calculator package pin must be an object")
    role = calculator.get("role")
    if calculator.get("name") != "spm-calculator" or role not in (
        "runtime_dependency",
        "country_dependency",
    ):
        raise ValueError("spm-calculator must be an explicit runtime_dependency")
    # A protective `country_dependency` pin declares a compatible version only.
    # A `runtime_dependency` pin additionally carries the registry-verified
    # wheel identity that the promotion gate below requires.
    verified = role == "runtime_dependency"
    if calculator.get("country") != "us":
        raise ValueError("spm-calculator must be scoped to country us")
    if calculator.get("installable", True) is not True or calculator.get("markers"):
        raise ValueError("spm-calculator must be installed unconditionally for US")
    sha256 = calculator.get("sha256")
    if verified and (
        not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256)
    ):
        raise ValueError("spm-calculator requires its wheel sha256")
    version = calculator.get("version")
    if not _is_normalized_version(version):
        raise ValueError("spm-calculator requires an exact normalized version")
    requirement = calculator.get("install_requirement")
    expected_requirement = f"spm-calculator=={version}"
    if calculator.get("markers"):
        expected_requirement += f"; {calculator['markers']}"
    if requirement is not None and requirement != expected_requirement:
        raise ValueError(
            "spm-calculator install_requirement must match its exact version"
        )
    extras = bundle.get("extras", {})
    if not isinstance(extras, Mapping):
        raise ValueError("Bundle extras must be an object")
    for extra in ("us", "models"):
        entries = extras.get(extra, [])
        if not isinstance(entries, list) or "spm-calculator" not in entries:
            raise ValueError(f"spm-calculator must be included in the {extra} extra")
    if require_published_spm:
        if not verified:
            raise ValueError("SPM promotion pending: no published spm-calculator pin")
        if bundle.get("development"):
            raise ValueError(
                "Development fixtures are not certified production bundles"
            )
        wheel_url = calculator.get("wheel_url")
        if not isinstance(wheel_url, str):
            raise ValueError("Published SPM pin check requires a published PyPI wheel")
        url = urlparse(wheel_url)
        if url.scheme != "https" or url.hostname != "files.pythonhosted.org":
            raise ValueError("Published SPM pin check requires a published PyPI wheel")
