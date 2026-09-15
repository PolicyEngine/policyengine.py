"""SPM bundle pins and explicitly uncertified local-wheel development fixtures."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import zipfile
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlparse

import requests
from generate_bundle_artifacts import normalized_manifest
from packaging.version import Version

from policyengine.provenance.bundle_validation import validate_bundle_measurements
from policyengine.provenance.spm_configuration import SPMMeasurementConfiguration


def _calculator_component(version: str, sha256: str, wheel_url: str) -> dict:
    return {
        "name": "spm-calculator",
        "import_name": "spm_calculator",
        "version": version,
        "role": "runtime_dependency",
        "country": "us",
        "sha256": sha256,
        "wheel_url": wheel_url,
    }


def published_calculator_component(version: str) -> dict:
    """Read authoritative registry metadata and verify the actual wheel bytes."""
    if str(Version(version)) != version:
        raise ValueError("Pass an exact normalized calculator version")
    response = requests.get(
        f"https://pypi.org/pypi/spm-calculator/{version}/json", timeout=60
    )
    response.raise_for_status()
    metadata = response.json()
    if metadata["info"]["version"] != version:
        raise ValueError("Registry returned a different calculator version")
    wheels = [
        entry
        for entry in metadata.get("urls", [])
        if entry.get("packagetype") == "bdist_wheel"
        and entry.get("filename", "").endswith("-py3-none-any.whl")
        and not entry.get("yanked")
    ]
    if len(wheels) != 1:
        raise ValueError("Expected exactly one non-yanked universal calculator wheel")
    wheel = wheels[0]
    url = urlparse(wheel["url"])
    if url.scheme != "https" or url.hostname != "files.pythonhosted.org":
        raise ValueError("Calculator wheel must be published on files.pythonhosted.org")
    expected = wheel.get("digests", {}).get("sha256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Registry wheel metadata has no valid sha256")
    download = requests.get(wheel["url"], timeout=60)
    download.raise_for_status()
    if hashlib.sha256(download.content).hexdigest() != expected:
        raise ValueError(
            "Published calculator wheel bytes do not match registry sha256"
        )
    return _calculator_component(version, expected, wheel["url"])


def configure_spm(bundle: dict, configuration: dict, calculator: dict | None) -> dict:
    """Stage measurement defaults and, when available, a verified runtime pin."""
    updated = copy.deepcopy(bundle)
    updated.setdefault("measurements", {})["spm"] = (
        SPMMeasurementConfiguration.model_validate(configuration).model_dump(
            mode="json"
        )
    )
    if calculator is not None:
        updated["packages"]["spm-calculator"] = calculator
        for extra in ("us", "models"):
            entries = updated["extras"][extra]
            if "spm-calculator" not in entries:
                entries.append("spm-calculator")
    validate_bundle_measurements(updated)
    return normalized_manifest(updated)


def local_wheel_component(path: Path, expected_name: str) -> dict:
    """Extract actual wheel metadata and hash, without registry identity claims."""
    path = path.resolve(strict=True)
    with zipfile.ZipFile(path) as archive:
        metadata_paths = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_paths) != 1:
            raise ValueError("Wheel must contain exactly one METADATA file")
        metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
    if metadata["Name"].lower().replace("_", "-") != expected_name:
        raise ValueError(f"Expected {expected_name} wheel, got {metadata['Name']}")
    version = str(Version(metadata["Version"]))
    return {
        "name": expected_name,
        "version": version,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "wheel_url": path.as_uri(),
    }


def development_manifest(
    bundle: dict, country_wheel: Path, calculator_wheel: Path
) -> dict:
    """Build a local test identity, stripping the inherited US certification."""
    country = local_wheel_component(country_wheel, "policyengine-us")
    calculator = local_wheel_component(calculator_wheel, "spm-calculator")
    updated = copy.deepcopy(bundle)
    updated["packages"]["policyengine-us"].update(country)
    updated["data_releases"]["us"]["model_package"] = country
    updated["data_releases"]["us"].pop("certification", None)
    updated["data_releases"]["us"].pop("certified_data_artifact", None)
    updated["development"] = {
        "purpose": "local canonical SPM wrapper tests",
        "data_certification": "not_certified",
        "promotion_status": "pending",
        "data_release_metadata": "inherited reference only; no compatibility claim",
        "local_wheels": {"policyengine-us": country, "spm-calculator": calculator},
    }
    return configure_spm(
        updated,
        bundle["measurements"]["spm"],
        _calculator_component(
            calculator["version"], calculator["sha256"], calculator["wheel_url"]
        ),
    )


def write_development_manifest(
    bundle: dict, country_wheel: Path, calculator_wheel: Path, output: Path
) -> dict:
    """Write an explicitly local development fixture, never the packaged manifest."""
    from generate_bundle_artifacts import BUNDLE_MANIFEST

    if output.resolve() == BUNDLE_MANIFEST.resolve():
        raise ValueError("Development fixtures cannot overwrite the packaged manifest")
    manifest = development_manifest(bundle, country_wheel, calculator_wheel)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest
