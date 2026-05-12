from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

BUNDLE_REPOSITORY = "PolicyEngine/policyengine-bundles"
BUNDLE_ARCHIVE_URL = (
    "https://github.com/"
    + BUNDLE_REPOSITORY
    + "/releases/download/v{version}/policyengine-bundle-{version}.tar.gz"
)
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "src" / "policyengine" / "data"
PYPROJECT = REPO_ROOT / "pyproject.toml"
MICRODATA_KIND = "microdata"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vendor a released policyengine-bundles archive into .py."
    )
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--archive",
        type=Path,
        help="Optional local policyengine-bundle-{version}.tar.gz archive.",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        archive_path = (
            args.archive or temp_root / f"policyengine-bundle-{args.version}.tar.gz"
        )
        if args.archive is None:
            _download_bundle_archive(args.version, archive_path)
        bundle_root = _extract_bundle_archive(archive_path, temp_root, args.version)
        _vendor_bundle(bundle_root, DATA_ROOT, PYPROJECT)

    print(f"Vendored policyengine bundle {args.version}.")
    return 0


def _download_bundle_archive(version: str, destination: Path) -> None:
    url = BUNDLE_ARCHIVE_URL.format(version=version)
    request = urllib.request.Request(url, headers={"User-Agent": "policyengine.py"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request, timeout=120) as response:
        with destination.open("wb") as file:
            shutil.copyfileobj(response, file)


def _extract_bundle_archive(
    archive_path: Path,
    temp_root: Path,
    version: str,
) -> Path:
    extract_root = temp_root / "bundle"
    extract_root.mkdir()
    with tarfile.open(archive_path) as archive:
        _validate_archive_members(archive, extract_root)
        archive.extractall(extract_root)

    expected_root = extract_root / f"policyengine-bundle-{version}"
    if expected_root.is_dir():
        return expected_root
    roots = [path for path in extract_root.iterdir() if path.is_dir()]
    if len(roots) == 1:
        return roots[0]
    raise ValueError(f"Could not find bundle root in {archive_path}.")


def _validate_archive_members(archive: tarfile.TarFile, extract_root: Path) -> None:
    resolved_root = extract_root.resolve()
    for member in archive.getmembers():
        destination = (extract_root / member.name).resolve()
        if not destination.is_relative_to(resolved_root):
            raise ValueError(f"Unsafe path in bundle archive: {member.name!r}.")


def _vendor_bundle(bundle_root: Path, data_root: Path, pyproject_path: Path) -> None:
    bundle = _load_json(bundle_root / "bundle.json")
    _require_bundle_payload(bundle_root, bundle)

    data_root.mkdir(parents=True, exist_ok=True)
    _copy_file(bundle_root / "bundle.json", data_root / "bundle.json")
    _replace_tree(bundle_root / "countries", data_root / "countries")
    _replace_tree(bundle_root / "install", data_root / "install")
    _copy_file(
        bundle_root / str(bundle["validation_report"]),
        data_root / str(bundle["validation_report"]),
    )
    _write_release_manifests(bundle, data_root)
    _update_pyproject_pins(bundle, pyproject_path)


def _require_bundle_payload(bundle_root: Path, bundle: dict[str, Any]) -> None:
    for path in [
        "bundle.json",
        bundle.get("validation_report"),
        "countries",
        "install",
    ]:
        if path is None:
            raise ValueError("Bundle manifest does not define validation_report.")
        if not (bundle_root / str(path)).exists():
            raise ValueError(f"Bundle archive is missing {path}.")
    for relative_path in bundle.get("countries", {}).values():
        if not (bundle_root / str(relative_path)).is_file():
            raise ValueError(f"Bundle archive is missing {relative_path}.")


def _replace_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _write_release_manifests(bundle: dict[str, Any], data_root: Path) -> None:
    manifest_root = data_root / "release_manifests"
    manifest_root.mkdir(parents=True, exist_ok=True)
    for country_id, country_path in sorted(bundle.get("countries", {}).items()):
        country_bundle = _load_json(data_root / str(country_path))
        existing_path = manifest_root / f"{country_id}.json"
        existing = _load_json(existing_path) if existing_path.is_file() else {}
        manifest = _country_release_manifest(
            country_id=country_id,
            bundle=bundle,
            country_bundle=country_bundle,
            existing_manifest=existing,
        )
        existing_path.write_text(json.dumps(manifest, indent=2) + "\n")


def _country_release_manifest(
    *,
    country_id: str,
    bundle: dict[str, Any],
    country_bundle: dict[str, Any],
    existing_manifest: dict[str, Any],
) -> dict[str, Any]:
    bundle_version = str(bundle["bundle_version"])
    default_dataset = str(country_bundle["default_dataset"])
    datasets = country_bundle.get("datasets", {})
    default_artifact = datasets.get(default_dataset)
    if not isinstance(default_artifact, dict):
        raise ValueError(f"{country_id} default dataset is not present in bundle.")

    certification = country_bundle.get("certification", {})
    data_package = _data_package_reference(country_bundle)
    return {
        "schema_version": 1,
        "bundle_id": f"{country_id}-{bundle_version}",
        "country_id": country_id,
        "policyengine_version": bundle_version,
        "model_package": _package_version(country_bundle["model_package"]),
        "data_package": data_package,
        "certified_data_artifact": {
            "data_package": {
                "name": data_package["name"],
                "version": data_package["version"],
            },
            "build_id": certification.get("data_build_id"),
            "dataset": default_dataset,
            "uri": _policyengine_hf_uri(country_bundle, default_artifact),
            "sha256": default_artifact.get("sha256"),
        },
        "certification": {
            "compatibility_basis": certification.get("compatibility_basis"),
            "data_build_id": certification.get("data_build_id"),
            "built_with_model_version": (
                certification.get("built_with_model_package", {}).get("version")
            ),
            "certified_for_model_version": (
                certification.get("certified_for_model_package", {}).get("version")
            ),
            "data_build_fingerprint": certification.get("data_build_fingerprint"),
            "certified_by": "policyengine.py bundled manifest",
        },
        "default_dataset": default_dataset,
        "datasets": _dataset_path_references(country_bundle),
        "region_datasets": existing_manifest.get("region_datasets", {}),
    }


def _package_version(package: dict[str, Any]) -> dict[str, str]:
    payload = {
        "name": str(package["name"]),
        "version": str(package["version"]),
    }
    for field_name in ("sha256", "wheel_url"):
        value = package.get(field_name)
        if isinstance(value, str):
            payload[field_name] = value
    return payload


def _data_package_reference(country_bundle: dict[str, Any]) -> dict[str, str]:
    data_package = country_bundle["data_package"]
    artifact_release = country_bundle.get("artifact_release", {})
    payload = {
        "name": str(data_package["name"]),
        "version": str(data_package["version"]),
        "repo_id": str(data_package["repo_id"]),
        "repo_type": str(data_package.get("repo_type", "model")),
        "release_manifest_path": str(
            data_package.get("release_manifest_path", "release_manifest.json")
        ),
    }
    release_manifest_revision = artifact_release.get("version")
    if isinstance(release_manifest_revision, str):
        payload["release_manifest_revision"] = release_manifest_revision
    return payload


def _dataset_path_references(
    country_bundle: dict[str, Any],
) -> dict[str, dict[str, str]]:
    references = {}
    for dataset_name, artifact in country_bundle.get("datasets", {}).items():
        if artifact.get("kind") != MICRODATA_KIND:
            continue
        path = artifact.get("path")
        if isinstance(path, str):
            references[dataset_name] = {"path": path}
    return references


def _policyengine_hf_uri(
    country_bundle: dict[str, Any],
    artifact: dict[str, Any],
) -> str:
    path = artifact.get("path")
    if isinstance(path, str):
        repo_id = artifact.get("repo_id") or country_bundle["data_package"]["repo_id"]
        revision = artifact.get("revision") or country_bundle["data_package"]["version"]
        return f"hf://{repo_id}/{path}@{revision}"

    uri = artifact.get("uri")
    if isinstance(uri, str):
        return _bundle_hf_uri_to_policyengine_uri(uri)
    raise ValueError("Data artifact must define path or uri.")


def _bundle_hf_uri_to_policyengine_uri(uri: str) -> str:
    if not uri.startswith("hf://"):
        return uri
    remainder = uri.removeprefix("hf://")
    first_component, _, rest = remainder.partition("/")
    if first_component in {"model", "dataset"}:
        remainder = rest
    repo_id, separator, revision_and_path = remainder.partition("@")
    if not separator:
        return uri
    revision, separator, path = revision_and_path.partition("/")
    if not separator:
        return uri
    return f"hf://{repo_id}/{path}@{revision}"


def _update_pyproject_pins(bundle: dict[str, Any], pyproject_path: Path) -> None:
    text = pyproject_path.read_text()
    for package_name, package in sorted(bundle.get("packages", {}).items()):
        if package.get("role") == "bundle_carrier":
            continue
        version = package.get("version")
        if not isinstance(version, str):
            continue
        pattern = rf'("{re.escape(package_name)}==)[^"]+(")'
        text, replacements = re.subn(pattern, rf"\g<1>{version}\g<2>", text)
        if replacements == 0:
            raise ValueError(f"Could not find pyproject pin for {package_name}.")
    pyproject_path.write_text(text)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


if __name__ == "__main__":
    sys.exit(main())
