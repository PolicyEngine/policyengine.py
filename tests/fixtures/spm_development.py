"""Explicit test-only bootstrap for unpublished country/calculator wheels.

Load with ``-p tests.fixtures.spm_development --spm-development-manifest PATH``.
This bypass is never imported by production code or enabled by default pytest.
It supplies an UNVERIFIED receipt, not fabricated data compatibility evidence.
"""

import copy
import hashlib
import importlib
import json
import os
import sys
import zipfile
from importlib import metadata
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

_DEVELOPMENT_MANIFEST = None


def _verify_import_sources(packages):
    """Authenticate import resolution and already loaded modules, not just metadata.

    Distribution metadata can describe the right wheel while PYTHONPATH or a
    previously imported module supplies different code. Check without importing
    the country packages, then repeat after the explicit bootstrap imports them.
    """
    for import_name, (root, members) in packages.items():
        spec = importlib.util.find_spec(import_name)
        if spec is None or spec.origin is None:
            raise ValueError(f"Cannot authenticate import source for {import_name}")
        expected_init = root / "__init__.py"
        if Path(spec.origin).resolve() != expected_init:
            raise ValueError(
                f"Unexpected import source for {import_name}: {spec.origin}"
            )
        if {Path(p).resolve() for p in spec.submodule_search_locations or ()} != {root}:
            raise ValueError(f"Unexpected package search path for {import_name}")
        for name, module in tuple(sys.modules.items()):
            if name != import_name and not name.startswith(import_name + "."):
                continue
            if module is None:
                continue
            source = getattr(module, "__file__", None)
            module_spec = getattr(module, "__spec__", None)
            if (
                source is None
                and module_spec is not None
                and module_spec.origin is None
                and module_spec.submodule_search_locations
            ):
                # Country parameter directories are legitimate namespace
                # packages. Every namespace search directory must still belong
                # to the authenticated installation and wheel inventory.
                locations = {
                    Path(p).resolve() for p in module_spec.submodule_search_locations
                }
                if locations != {
                    Path(p).resolve() for p in getattr(module, "__path__", ())
                }:
                    raise ValueError(
                        f"Unexpected loaded package search path for {name}"
                    )
                for location in locations:
                    try:
                        prefix = location.relative_to(root).as_posix() + "/"
                    except ValueError as exc:
                        raise ValueError(
                            f"Unexpected loaded import source for {name}"
                        ) from exc
                    if members is not None and not any(
                        member.startswith(prefix) for member in members
                    ):
                        raise ValueError(f"Unexpected loaded import source for {name}")
                continue
            if not source or module_spec is None or module_spec.origin is None:
                raise ValueError(f"Cannot authenticate loaded import source for {name}")
            source = Path(source).resolve()
            try:
                relative = source.relative_to(root).as_posix()
            except ValueError as exc:
                raise ValueError(f"Unexpected loaded import source for {name}") from exc
            if Path(module_spec.origin).resolve() != source or (
                members is not None and relative not in members
            ):
                raise ValueError(f"Unexpected loaded import source for {name}")
            if hasattr(module, "__path__") and {
                Path(p).resolve() for p in module.__path__
            } != {source.parent}:
                raise ValueError(f"Unexpected loaded package search path for {name}")


def pytest_addoption(parser):
    parser.addoption("--spm-development-manifest", type=Path)


def pytest_load_initial_conftests(early_config, parser, args):
    path = early_config.known_args_namespace.spm_development_manifest
    if path is None:
        raise pytest.UsageError(
            "The SPM development plugin requires an explicit manifest"
        )
    try:
        activate_spm_development_manifest(path)
    except ValueError as exc:
        raise pytest.UsageError(str(exc)) from exc


def _verify_local_wheel_installations(payload):
    """Require both fixture wheel identity and installed source byte identity."""
    packages = {}
    for name, import_name in (
        ("policyengine-us", "policyengine_us"),
        ("spm-calculator", "spm_calculator"),
    ):
        component = payload["packages"][name]
        if component["import_name"] != import_name:
            raise ValueError(f"Unexpected import name for {name}")
        uri = urlparse(component["wheel_url"])
        if uri.scheme != "file" or uri.netloc:
            raise ValueError("Development fixtures require explicit local wheel files")
        path = Path(unquote(uri.path))
        if hashlib.sha256(path.read_bytes()).hexdigest() != component["sha256"]:
            raise ValueError(f"Local {name} wheel does not match the fixture sha256")
        distribution = metadata.distribution(name)
        members = set()
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if not member.startswith(import_name + "/") or member.endswith("/"):
                    continue
                installed = distribution.locate_file(member)
                if not installed.is_file() or installed.read_bytes() != archive.read(
                    member
                ):
                    raise ValueError(
                        f"Installed {name} file differs from wheel: {member}"
                    )
                members.add(member[len(import_name) + 1 :])
        if not members:
            raise ValueError(f"Local {name} wheel contains no package files")
        packages[import_name] = (
            Path(distribution.locate_file(import_name)).resolve(),
            members,
        )
    # Core's version is pinned in the fixture; its wheel is authenticated by the
    # separate four-wheel producer probe. Still reject a shadowed core import.
    packages["policyengine_core"] = (
        Path(
            metadata.distribution("policyengine-core").locate_file("policyengine_core")
        ).resolve(),
        None,
    )
    _verify_import_sources(packages)
    return packages


def activate_spm_development_manifest(path):
    """Explicitly bootstrap an unpublished local runtime before country imports.

    This test helper is also available to bounded development scripts. It never
    certifies the inherited data and refuses a mismatched installed wheel.
    """
    global _DEVELOPMENT_MANIFEST

    if "policyengine.tax_benefit_models.us.model" in sys.modules:
        raise ValueError(
            "Activate the development fixture before importing country models"
        )
    path = Path(path)
    payload = json.loads(path.read_text())
    if payload.get("development", {}).get("data_certification") != "not_certified":
        raise ValueError("The SPM plugin only accepts uncertified development fixtures")
    for name in ("policyengine-us", "policyengine-core", "spm-calculator"):
        if metadata.version(name) != payload["packages"][name]["version"]:
            raise ValueError(f"Installed {name} does not match the development fixture")
    packages = _verify_local_wheel_installations(payload)
    os.environ["POLICYENGINE_SKIP_COUNTRY_IMPORTS"] = "1"
    import policyengine
    from policyengine import bundle
    from policyengine.provenance import manifest

    _DEVELOPMENT_MANIFEST = payload
    original_release = manifest.get_release_manifest
    original_certify = manifest.certify_data_release_compatibility

    def development_release(country_id):
        if country_id == "us":
            return manifest.CountryReleaseManifest.model_validate(
                copy.deepcopy(payload["data_releases"]["us"])
            )
        return original_release(country_id)

    def unavailable_data_release(country_id):
        raise manifest.DataReleaseManifestUnavailableError(
            "Explicit offline local-wheel development fixture; data certification pending"
        )

    def unverified_development(country_id, runtime_model_version, **kwargs):
        if country_id == "us":
            return manifest.DataCertification(
                compatibility_basis="unverified_development_fixture",
                certified_for_model_version=runtime_model_version,
            )
        return original_certify(country_id, runtime_model_version, **kwargs)

    manifest.get_release_manifest = development_release
    manifest.get_data_release_manifest = unavailable_data_release
    manifest.certify_data_release_compatibility = unverified_development
    bundle.get_current_bundle = lambda: copy.deepcopy(payload)
    policyengine.us = importlib.import_module("policyengine.tax_benefit_models.us")
    if importlib.util.find_spec("policyengine_uk") is not None:
        policyengine.uk = importlib.import_module("policyengine.tax_benefit_models.uk")
    _verify_import_sources(packages)
    return copy.deepcopy(payload)


@pytest.fixture
def spm_development_bundle():
    """Expose the explicitly enabled, unverified fixture for test assertions."""
    return copy.deepcopy(_DEVELOPMENT_MANIFEST)
