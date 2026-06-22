"""PolicyEngine bundle installation and verification helpers.

The bundle manifest is packaged with ``policyengine`` and names the exact
first-party packages plus certified data artifacts for a PolicyEngine release.
This module keeps installation pip-based while adding the dataset handling that
plain pip cannot provide.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import venv as venv_module
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from importlib.resources import files
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence
from urllib.parse import quote

import requests

BUNDLE_MANIFEST_RESOURCE = ("data", "stack", "manifest.json")
BUNDLE_HISTORY_RESOURCE = ("data", "bundles")
DEFAULT_COUNTRIES = ("us", "uk")
DEFAULT_DATA_DIR = Path("./data")
RECEIPT_FILENAME = ".policyengine-bundle.json"
BACKUP_DIR_NAME = ".policyengine-bundle-backups"
DOWNLOAD_TIMEOUT_SECONDS = 60


class BundleError(ValueError):
    """Raised when bundle metadata or local installation state is invalid."""


@dataclass(frozen=True)
class DatasetPlan:
    country: str
    dataset: str
    uri: str
    filename: str
    data_version: Optional[str]
    release_manifest_uri: Optional[str]
    provider: str
    destination: Path


def _bundle_resource_path():
    path = files("policyengine")
    for part in BUNDLE_MANIFEST_RESOURCE:
        path = path.joinpath(part)
    return path


def _bundle_history_path(version: str):
    path = files("policyengine")
    for part in BUNDLE_HISTORY_RESOURCE:
        path = path.joinpath(part)
    return path.joinpath(f"{version}.json")


def _normalise_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    bundle_version = (
        payload.get("bundle_version")
        or payload.get("stack_version")
        or payload.get("policyengine_version")
    )
    if not bundle_version:
        raise BundleError("Bundle manifest is missing a bundle version.")
    payload["bundle_version"] = str(bundle_version)
    payload.setdefault("stack_version", str(bundle_version))
    payload.setdefault("policyengine_version", str(bundle_version))
    payload.setdefault("countries", {})
    payload.setdefault("packages", {})
    payload.setdefault("extras", {})
    payload.setdefault("data_releases", _data_releases_from_countries(payload))
    return payload


def _data_releases_from_countries(manifest: Mapping[str, Any]) -> dict[str, Any]:
    releases: dict[str, Any] = {}
    packages = manifest.get("packages", {})
    for country, country_meta in manifest.get("countries", {}).items():
        if not isinstance(country_meta, Mapping):
            continue
        data_package_name = country_meta.get("data_package")
        data_package = (
            packages.get(data_package_name, {})
            if isinstance(data_package_name, str) and isinstance(packages, Mapping)
            else {}
        )
        data_version = (
            country_meta.get("data_artifact_version")
            or country_meta.get("data_version")
            or data_package.get("version")
        )
        releases[str(country)] = {
            "provider": country_meta.get("data_provider", "legacy"),
            "data_package": data_package_name,
            "version": data_version,
            "default_dataset": country_meta.get("default_dataset"),
            "default_dataset_uri": country_meta.get("default_dataset_uri"),
            "release_manifest_uri": country_meta.get("release_manifest_uri"),
        }
    return releases


def get_current_bundle() -> dict[str, Any]:
    """Return the bundle manifest packaged with this ``policyengine`` wheel."""

    resource = _bundle_resource_path()
    try:
        return _normalise_manifest(json.loads(resource.read_text()))
    except FileNotFoundError as exc:
        raise BundleError("No packaged PolicyEngine bundle manifest found.") from exc


def load_bundle_manifest(
    version: Optional[str] = None,
    *,
    manifest_ref: Optional[str] = None,
) -> dict[str, Any]:
    """Load a packaged, historical, or custom bundle manifest."""

    if manifest_ref:
        if manifest_ref.startswith(("http://", "https://")):
            response = requests.get(manifest_ref, timeout=DOWNLOAD_TIMEOUT_SECONDS)
            response.raise_for_status()
            return _normalise_manifest(response.json())
        return _normalise_manifest(json.loads(Path(manifest_ref).read_text()))

    current = get_current_bundle()
    if version in (None, "latest", current["bundle_version"]):
        return current

    history_path = _bundle_history_path(str(version))
    if history_path.is_file():
        return _normalise_manifest(json.loads(history_path.read_text()))
    raise BundleError(
        f"Bundle {version!r} is not packaged with this policyengine release."
    )


def normalise_countries(
    countries: Optional[Sequence[str]],
    manifest: Optional[Mapping[str, Any]] = None,
) -> list[str]:
    manifest = manifest or get_current_bundle()
    available = set(manifest.get("countries", {}) or DEFAULT_COUNTRIES)
    selected = list(countries or sorted(available))
    normalised = []
    for country in selected:
        country_id = country.lower()
        if country_id not in available:
            raise BundleError(f"Unsupported bundle country: {country}")
        if country_id not in normalised:
            normalised.append(country_id)
    return normalised


def bundle_install_requirements(
    manifest: Optional[Mapping[str, Any]] = None,
    *,
    countries: Optional[Sequence[str]] = None,
) -> list[str]:
    """Return exact pip requirements for the selected bundle package scaffold."""

    bundle = _normalise_manifest(manifest or get_current_bundle())
    selected = set(normalise_countries(countries, bundle))
    requirements: list[str] = []
    for key, component in bundle.get("packages", {}).items():
        if not _include_component(str(key), component, selected):
            continue
        requirements.append(
            component.get("install_requirement") or _requirement(component)
        )
    return requirements


def _include_component(
    key: str,
    component: Mapping[str, Any],
    countries: set[str],
) -> bool:
    if component.get("installable") is False:
        return False
    role = component.get("role")
    country = component.get("country")
    if role in {"stack_carrier", "bundle_carrier", "runtime_dependency"}:
        return True
    if isinstance(country, str):
        return country in countries
    if role in {"data_provider", "dataset_provider"}:
        return True
    return key == "policyengine"


def _requirement(component: Mapping[str, Any]) -> str:
    requirement = f"{component['name']}=={component['version']}"
    markers = component.get("markers")
    if markers:
        requirement += f"; {markers}"
    return requirement


def resolve_target_python(
    *,
    python: Optional[str] = None,
    venv: Optional[Path] = None,
) -> Path:
    """Resolve the Python interpreter that package installation should target."""

    if python and venv:
        raise BundleError("Pass either --python or --venv, not both.")
    if venv is not None:
        return _ensure_venv(venv)
    if python:
        candidate = Path(shutil.which(python) or python)
        if not candidate.exists():
            raise BundleError(f"Python interpreter not found: {python}")
        return candidate

    active_env = os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")
    if active_env:
        candidate = Path(active_env) / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        if _looks_like_runner_env(candidate):
            raise BundleError(
                "The active Python appears to be a uvx/pipx runner environment. "
                "Pass --venv or --python to choose the installation target."
            )
        if candidate.exists():
            return candidate
    raise BundleError("Pass --venv or --python to choose the installation target.")


def _ensure_venv(path: Path) -> Path:
    if not path.exists():
        venv_module.EnvBuilder(with_pip=True).create(str(path))
    python = path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        raise BundleError(f"Virtualenv at {path} does not contain Python.")
    return python


def _looks_like_runner_env(python: Path) -> bool:
    text = str(python).lower()
    return "uvx" in text or "pipx" in text or "/uv/tools/" in text


def install_package_scaffold(
    target_python: Path,
    requirements: Sequence[str],
    *,
    dry_run: bool = False,
) -> None:
    command = [str(target_python), "-m", "pip", "install", *requirements]
    if dry_run:
        print(" ".join(command))
        return
    subprocess.run(command, check=True)


def dataset_plans(
    manifest: Optional[Mapping[str, Any]] = None,
    *,
    countries: Optional[Sequence[str]] = None,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> list[DatasetPlan]:
    bundle = _normalise_manifest(manifest or get_current_bundle())
    releases = bundle.get("data_releases") or _data_releases_from_countries(bundle)
    plans: list[DatasetPlan] = []
    for country in normalise_countries(countries, bundle):
        release = releases.get(country, {}) if isinstance(releases, Mapping) else {}
        uri = release.get("default_dataset_uri")
        dataset = release.get("default_dataset")
        if not uri or not dataset:
            continue
        filename = _filename_from_uri(str(uri))
        plans.append(
            DatasetPlan(
                country=country,
                dataset=str(dataset),
                uri=str(uri),
                filename=filename,
                data_version=(
                    str(release["version"])
                    if release.get("version") is not None
                    else None
                ),
                release_manifest_uri=(
                    str(release["release_manifest_uri"])
                    if release.get("release_manifest_uri")
                    else None
                ),
                provider=str(release.get("provider") or "legacy"),
                destination=data_dir / filename,
            )
        )
    return plans


def _filename_from_uri(uri: str) -> str:
    without_revision = uri.rsplit("@", 1)[0]
    if without_revision.startswith("hf://"):
        return (
            without_revision.removeprefix("hf://").split("/", 2)[2].rsplit("/", 1)[-1]
        )
    if without_revision.startswith("gs://"):
        return (
            without_revision.removeprefix("gs://").split("/", 1)[1].rsplit("/", 1)[-1]
        )
    return Path(without_revision).name


def install_datasets(
    manifest: Mapping[str, Any],
    *,
    countries: Optional[Sequence[str]] = None,
    data_dir: Path = DEFAULT_DATA_DIR,
    yes: bool = False,
    dry_run: bool = False,
    session=requests,
) -> list[dict[str, Any]]:
    plans = dataset_plans(manifest, countries=countries, data_dir=data_dir)
    if not plans:
        return []
    _confirm_dataset_install(plans, data_dir=data_dir, yes=yes, dry_run=dry_run)
    installed = []
    for plan in plans:
        if dry_run:
            print(f"download {plan.uri} -> {plan.destination}")
            installed.append(_receipt_dataset(plan))
            continue
        downloaded = _download_to_temp(plan, data_dir=data_dir, session=session)
        try:
            _backup_existing(plan.destination)
            plan.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(downloaded), str(plan.destination))
        finally:
            if downloaded.exists():
                downloaded.unlink()
        installed.append(_receipt_dataset(plan))
    return installed


def _confirm_dataset_install(
    plans: Sequence[DatasetPlan],
    *,
    data_dir: Path,
    yes: bool,
    dry_run: bool,
) -> None:
    countries = ", ".join(plan.country for plan in plans)
    print(
        "This will download certified PolicyEngine datasets for "
        f"{countries} into {data_dir}."
    )
    print(
        "Existing matching dataset files will be moved to "
        f"{data_dir / BACKUP_DIR_NAME}/<timestamp>/."
    )
    if yes or dry_run:
        return
    answer = input("Continue? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        raise BundleError("Dataset installation cancelled.")


def _download_to_temp(plan: DatasetPlan, *, data_dir: Path, session=requests) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    url = _download_url(plan.uri)
    headers = _auth_headers(plan.uri)
    suffix = Path(plan.filename).suffix or ".download"
    fd, temp_name = tempfile.mkstemp(
        prefix=".policyengine-download-", suffix=suffix, dir=data_dir
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with session.get(
            url,
            headers=headers,
            stream=True,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        ) as response:
            if response.status_code in {401, 403}:
                raise BundleError(
                    f"Could not download {plan.country.upper()} dataset. "
                    "If this is a private Hugging Face dataset, set HUGGING_FACE_TOKEN."
                )
            response.raise_for_status()
            with temp_path.open("wb") as stream:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        stream.write(chunk)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
    return temp_path


def _download_url(uri: str) -> str:
    without_revision, revision = _split_revision(uri)
    if without_revision.startswith("hf://"):
        parts = without_revision.removeprefix("hf://").split("/", 2)
        if len(parts) != 3:
            raise BundleError(f"Invalid Hugging Face dataset URI: {uri}")
        repo_id = f"{parts[0]}/{parts[1]}"
        path = parts[2]
        if not revision:
            raise BundleError(f"Hugging Face dataset URI must pin a revision: {uri}")
        return f"https://huggingface.co/{repo_id}/resolve/{quote(revision)}/{path}"
    if without_revision.startswith("gs://"):
        bucket_and_path = without_revision.removeprefix("gs://")
        bucket, _, path = bucket_and_path.partition("/")
        return f"https://storage.googleapis.com/{bucket}/{quote(path)}"
    if without_revision.startswith(("http://", "https://")):
        return uri
    return uri


def _split_revision(uri: str) -> tuple[str, Optional[str]]:
    if "@" not in uri:
        return uri, None
    without_revision, revision = uri.rsplit("@", 1)
    return without_revision, revision


def _auth_headers(uri: str) -> dict[str, str]:
    if not uri.startswith(("hf://", "https://huggingface.co/")):
        return {}
    token = (
        os.environ.get("HUGGING_FACE_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    )
    return {"Authorization": f"Bearer {token}"} if token else {}


def _backup_existing(path: Path) -> None:
    if not path.exists():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = path.parent / BACKUP_DIR_NAME / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(backup_dir / path.name))


def _receipt_dataset(plan: DatasetPlan) -> dict[str, Any]:
    return {
        "country": plan.country,
        "dataset": plan.dataset,
        "version": plan.data_version,
        "uri": plan.uri,
        "path": str(plan.destination),
        "release_manifest_uri": plan.release_manifest_uri,
        "provider": plan.provider,
    }


def write_receipt(
    manifest: Mapping[str, Any],
    *,
    data_dir: Path,
    countries: Sequence[str],
    datasets: Sequence[Mapping[str, Any]],
) -> Path:
    receipt = {
        "schema_version": 1,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "bundle_version": manifest["bundle_version"],
        "policyengine_version": manifest["policyengine_version"],
        "countries": list(countries),
        "packages": manifest.get("packages", {}),
        "datasets": list(datasets),
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / RECEIPT_FILENAME
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return path


def read_receipt(data_dir: Path = DEFAULT_DATA_DIR) -> Optional[dict[str, Any]]:
    path = data_dir / RECEIPT_FILENAME
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def install_bundle(
    version: Optional[str] = None,
    *,
    manifest_ref: Optional[str] = None,
    python: Optional[str] = None,
    venv: Optional[Path] = None,
    countries: Optional[Sequence[str]] = None,
    data_dir: Path = DEFAULT_DATA_DIR,
    no_datasets: bool = False,
    yes: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    manifest = load_bundle_manifest(version, manifest_ref=manifest_ref)
    selected_countries = normalise_countries(countries, manifest)
    requirements = bundle_install_requirements(manifest, countries=selected_countries)
    target_python = resolve_target_python(python=python, venv=venv)
    install_package_scaffold(target_python, requirements, dry_run=dry_run)
    installed_datasets: list[dict[str, Any]] = []
    if not no_datasets:
        installed_datasets = install_datasets(
            manifest,
            countries=selected_countries,
            data_dir=data_dir,
            yes=yes,
            dry_run=dry_run,
        )
        if not dry_run:
            write_receipt(
                manifest,
                data_dir=data_dir,
                countries=selected_countries,
                datasets=installed_datasets,
            )
    return {
        "bundle_version": manifest["bundle_version"],
        "requirements": requirements,
        "countries": selected_countries,
        "datasets": installed_datasets,
        "data_dir": str(data_dir),
    }


def inspect_bundle_status(
    version: Optional[str] = None,
    *,
    manifest_ref: Optional[str] = None,
    countries: Optional[Sequence[str]] = None,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> dict[str, Any]:
    manifest = load_bundle_manifest(version, manifest_ref=manifest_ref)
    selected_countries = normalise_countries(countries, manifest)
    package_checks = [
        _package_check(component)
        for component in _selected_components(manifest, selected_countries)
    ]
    receipt = read_receipt(data_dir)
    dataset_checks = _dataset_checks(manifest, selected_countries, data_dir, receipt)
    passed = all(
        check["status"] == "ok" for check in [*package_checks, *dataset_checks]
    )
    return {
        "schema_version": 1,
        "bundle_version": manifest["bundle_version"],
        "policyengine_version": manifest["policyengine_version"],
        "countries": selected_countries,
        "matched": passed,
        "packages": package_checks,
        "datasets": dataset_checks,
        "receipt": receipt,
    }


def _selected_components(
    manifest: Mapping[str, Any], countries: Sequence[str]
) -> Iterable[Mapping[str, Any]]:
    selected = set(countries)
    for key, component in manifest.get("packages", {}).items():
        if _include_component(str(key), component, selected):
            yield component


def _package_check(component: Mapping[str, Any]) -> dict[str, Any]:
    package_name = str(component["name"])
    expected = str(component["version"])
    check: dict[str, Any] = {
        "package": package_name,
        "expected_version": expected,
    }
    try:
        installed = metadata.version(package_name)
    except metadata.PackageNotFoundError:
        check["status"] = "missing"
        return check
    check["installed_version"] = installed
    check["status"] = "ok" if installed == expected else "mismatch"
    return check


def _dataset_checks(
    manifest: Mapping[str, Any],
    countries: Sequence[str],
    data_dir: Path,
    receipt: Optional[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    receipt_datasets = {}
    if isinstance(receipt, Mapping):
        for dataset in receipt.get("datasets", []):
            if isinstance(dataset, Mapping) and dataset.get("country"):
                receipt_datasets[str(dataset["country"])] = dataset
    checks = []
    for plan in dataset_plans(manifest, countries=countries, data_dir=data_dir):
        check: dict[str, Any] = {
            "country": plan.country,
            "dataset": plan.dataset,
            "expected_version": plan.data_version,
            "expected_path": str(plan.destination),
        }
        receipt_dataset = receipt_datasets.get(plan.country)
        if receipt_dataset is None:
            check["status"] = "missing_receipt"
        elif receipt_dataset.get("version") != plan.data_version:
            check["status"] = "mismatch"
            check["installed_version"] = receipt_dataset.get("version")
        elif not Path(str(receipt_dataset.get("path", plan.destination))).exists():
            check["status"] = "missing_file"
        else:
            check["status"] = "ok"
            check["installed_version"] = receipt_dataset.get("version")
            check["path"] = receipt_dataset.get("path")
        checks.append(check)
    return checks
