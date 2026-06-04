from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Optional

DEFAULT_RELEASE_BASE_URL = (
    "https://github.com/PolicyEngine/policyengine-bundles/releases/download"
)
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_DIR = REPO_ROOT / "src" / "policyengine" / "data" / "bundle"
DEFAULT_RELEASE_MANIFEST_DIR = (
    REPO_ROOT / "src" / "policyengine" / "data" / "release_manifests"
)
DEFAULT_PYPROJECT = REPO_ROOT / "pyproject.toml"
DEFAULT_CHANGELOG_DIR = REPO_ROOT / "changelog.d"
COUNTRY_OPTIONAL_DEPENDENCIES = {
    "uk": "policyengine-uk",
    "us": "policyengine-us",
}


class BundleImportError(RuntimeError):
    """Raised when a PolicyEngine bundle cannot be imported into policyengine.py."""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import one policyengine-bundles release into policyengine.py. "
            "The script verifies release assets, vendors the exploded bundle, "
            "regenerates country release manifests, and updates country extras."
        )
    )
    parser.add_argument("version", help="Bundle version to import, e.g. 4.14.0.")
    parser.add_argument(
        "--dist-dir",
        type=Path,
        help="Use local release assets instead of downloading from GitHub.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_RELEASE_BASE_URL,
        help="GitHub release base URL used when --dist-dir is not provided.",
    )
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR)
    parser.add_argument(
        "--release-manifest-dir",
        type=Path,
        default=DEFAULT_RELEASE_MANIFEST_DIR,
    )
    parser.add_argument("--pyproject", type=Path, default=DEFAULT_PYPROJECT)
    parser.add_argument("--changelog-dir", type=Path, default=DEFAULT_CHANGELOG_DIR)
    parser.add_argument(
        "--no-changelog",
        action="store_true",
        help="Do not write a towncrier changelog fragment.",
    )
    args = parser.parse_args()

    try:
        imported = import_policyengine_bundle(
            version=args.version,
            dist_dir=args.dist_dir,
            base_url=args.base_url,
            bundle_dir=args.bundle_dir,
            release_manifest_dir=args.release_manifest_dir,
            pyproject_path=args.pyproject,
            changelog_dir=None if args.no_changelog else args.changelog_dir,
        )
    except BundleImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"imported bundle: {imported.bundle_dir}")
    for manifest_path in imported.release_manifest_paths:
        print(f"release manifest: {manifest_path}")
    print(f"updated pyproject: {imported.pyproject_path}")
    if imported.changelog_path is not None:
        print(f"changelog: {imported.changelog_path}")
    return 0


class ImportResult:
    def __init__(
        self,
        *,
        bundle_dir: Path,
        release_manifest_paths: list[Path],
        pyproject_path: Path,
        changelog_path: Optional[Path],
    ) -> None:
        self.bundle_dir = bundle_dir
        self.release_manifest_paths = release_manifest_paths
        self.pyproject_path = pyproject_path
        self.changelog_path = changelog_path


def import_policyengine_bundle(
    *,
    version: str,
    dist_dir: Optional[Path],
    base_url: str,
    bundle_dir: Path,
    release_manifest_dir: Path,
    pyproject_path: Path,
    changelog_dir: Optional[Path],
) -> ImportResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        assets_dir = dist_dir or temp_path / "dist"
        if dist_dir is None:
            _download_release_assets(
                version=version,
                output_dir=assets_dir,
                base_url=base_url,
            )

        archive_path, summary = _verify_release_assets(
            version=version,
            dist_dir=assets_dir,
        )
        unpacked_bundle_dir = _extract_bundle_archive(
            archive_path=archive_path,
            output_dir=temp_path / "unpacked",
            version=version,
        )
        _verify_bundle_digest(unpacked_bundle_dir, summary)

        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        shutil.copytree(unpacked_bundle_dir, bundle_dir)

    bundle = _load_json(bundle_dir / "bundle.json")
    country_manifest_paths = _write_country_release_manifests(
        bundle_dir=bundle_dir,
        bundle=bundle,
        release_manifest_dir=release_manifest_dir,
    )
    _update_optional_dependency_pins(
        pyproject_path=pyproject_path,
        bundle=bundle,
    )
    changelog_path = None
    if changelog_dir is not None:
        changelog_path = _write_changelog_fragment(
            changelog_dir=changelog_dir,
            version=version,
            bundle=bundle,
        )

    return ImportResult(
        bundle_dir=bundle_dir,
        release_manifest_paths=country_manifest_paths,
        pyproject_path=pyproject_path,
        changelog_path=changelog_path,
    )


def _download_release_assets(
    *,
    version: str,
    output_dir: Path,
    base_url: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for asset_name in _release_asset_names(version):
        url = f"{base_url.rstrip('/')}/v{version}/{asset_name}"
        output_path = output_dir / asset_name
        try:
            urllib.request.urlretrieve(url, output_path)
        except OSError as exc:
            raise BundleImportError(f"Could not download {url}: {exc}") from exc


def _verify_release_assets(*, version: str, dist_dir: Path) -> tuple[Path, dict]:
    archive_name, checksum_name, summary_name = _release_asset_names(version)
    archive_path = dist_dir / archive_name
    checksum_path = dist_dir / checksum_name
    summary_path = dist_dir / summary_name
    missing = [
        path.name
        for path in (archive_path, checksum_path, summary_path)
        if not path.exists()
    ]
    if missing:
        raise BundleImportError(f"Missing bundle release assets: {', '.join(missing)}.")

    summary = _load_json(summary_path)
    if summary.get("bundle_version") != version:
        raise BundleImportError(
            "Release summary bundle_version does not match requested version: "
            f"expected {version}, got {summary.get('bundle_version')}."
        )
    if summary.get("archive") != archive_name:
        raise BundleImportError(
            "Release summary archive name does not match expected asset: "
            f"expected {archive_name}, got {summary.get('archive')}."
        )

    checksum = _read_checksum_file(checksum_path, archive_name)
    if summary.get("archive_sha256") != checksum:
        raise BundleImportError(
            "Release summary archive_sha256 does not match checksum file: "
            f"expected {summary.get('archive_sha256')}, got {checksum}."
        )
    actual_checksum = _sha256_file(archive_path)
    if actual_checksum != checksum:
        raise BundleImportError(
            "Archive sha256 does not match checksum file: "
            f"expected {checksum}, got {actual_checksum}."
        )
    return archive_path, summary


def _extract_bundle_archive(
    *,
    archive_path: Path,
    output_dir: Path,
    version: str,
) -> Path:
    expected_root = f"policyengine-bundle-{version}"
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(archive_path) as archive:
            _validate_archive_members(archive, expected_root)
            if sys.version_info >= (3, 12):
                archive.extractall(output_dir, filter="data")
            else:
                archive.extractall(output_dir)
    except (tarfile.TarError, OSError) as exc:
        raise BundleImportError(f"Could not extract {archive_path}: {exc}") from exc

    bundle_dir = output_dir / expected_root
    if not bundle_dir.is_dir():
        raise BundleImportError(f"Archive did not contain {expected_root}/.")
    return bundle_dir


def _validate_archive_members(archive: tarfile.TarFile, expected_root: str) -> None:
    root = Path(expected_root)
    for member in archive.getmembers():
        member_path = Path(member.name)
        if member_path.is_absolute() or ".." in member_path.parts:
            raise BundleImportError(f"Unsafe archive member path: {member.name}")
        if member_path.parts[:1] != root.parts:
            raise BundleImportError(
                f"Archive member is outside {expected_root}/: {member.name}"
            )
        if member.issym() or member.islnk():
            raise BundleImportError(
                f"Archive link members are not allowed: {member.name}"
            )


def _verify_bundle_digest(bundle_dir: Path, summary: dict) -> None:
    expected = summary.get("bundle_digest")
    if not isinstance(expected, str) or not expected.startswith("sha256:"):
        raise BundleImportError("Release summary does not include bundle_digest.")
    actual = f"sha256:{_bundle_directory_digest(bundle_dir)}"
    if actual != expected:
        raise BundleImportError(
            "Release summary bundle_digest does not match unpacked bundle: "
            f"expected {expected}, got {actual}."
        )


def _bundle_directory_digest(bundle_dir: Path) -> str:
    hasher = hashlib.sha256()
    for relative_path in _bundle_files(bundle_dir):
        content = _normalized_file_content(bundle_dir, relative_path)
        hasher.update(relative_path.as_posix().encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(content.encode("utf-8"))
        hasher.update(b"\0")
    return hasher.hexdigest()


def _bundle_files(bundle_dir: Path) -> list[Path]:
    return sorted(
        path.relative_to(bundle_dir)
        for path in bundle_dir.rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    )


def _normalized_file_content(bundle_dir: Path, relative_path: Path) -> str:
    path = bundle_dir / relative_path
    if relative_path.suffix == ".json":
        payload = _load_json(path)
        if relative_path.as_posix() == "bundle.json":
            payload.pop("created_at", None)
            payload.pop("bundle_digest", None)
        elif relative_path.as_posix() == "validation-report.json":
            payload.pop("generated_at", None)
            checks = []
            for check in payload.get("checks", []):
                if not isinstance(check, dict):
                    checks.append(check)
                    continue
                check_payload = dict(check)
                check_payload.pop("command", None)
                check_payload.pop("started_at", None)
                check_payload.pop("ended_at", None)
                details = check_payload.get("details")
                if isinstance(details, dict):
                    details_payload = dict(details)
                    details_payload.pop("validated_on_platform", None)
                    check_payload["details"] = details_payload
                checks.append(check_payload)
            payload["checks"] = checks
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    text = path.read_text()
    if path.name in {"constraints.txt", "pylock.toml"}:
        return _strip_comment_lines(text)
    return text


def _strip_comment_lines(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _write_country_release_manifests(
    *,
    bundle_dir: Path,
    bundle: dict,
    release_manifest_dir: Path,
) -> list[Path]:
    country_paths = bundle.get("countries")
    if not isinstance(country_paths, dict) or not country_paths:
        raise BundleImportError("Bundle manifest does not include countries.")

    release_manifest_dir.mkdir(parents=True, exist_ok=True)
    written_paths = []
    for country_id, relative_path in sorted(country_paths.items()):
        if not isinstance(country_id, str) or not isinstance(relative_path, str):
            raise BundleImportError("Bundle countries must map ids to paths.")
        country_bundle = _load_json(bundle_dir / relative_path)
        release_manifest = _country_release_manifest(country_bundle)
        output_path = release_manifest_dir / f"{country_id}.json"
        _write_json(output_path, release_manifest)
        written_paths.append(output_path)
    return written_paths


def _country_release_manifest(country_bundle: dict) -> dict:
    country_id = _required_string(country_bundle, "country_id")
    bundle_version = _required_string(country_bundle, "bundle_version")
    data_package = _required_dict(country_bundle, "data_package")
    certification = _required_dict(country_bundle, "certification")
    datasets = _required_dict(country_bundle, "datasets")
    default_dataset = _required_string(country_bundle, "default_dataset")
    default_artifact = _required_dict(datasets, default_dataset)

    data_package_payload = {
        "name": _required_string(data_package, "name"),
        "version": _required_string(data_package, "version"),
        "repo_id": _required_string(data_package, "repo_id"),
        "repo_type": data_package.get("repo_type", "model"),
        "release_manifest_path": data_package.get(
            "release_manifest_path", "release_manifest.json"
        ),
    }
    release_manifest_revision = data_package.get("release_manifest_revision")
    if release_manifest_revision:
        data_package_payload["release_manifest_revision"] = release_manifest_revision

    return {
        "schema_version": 1,
        "bundle_id": f"{country_id}-{bundle_version}",
        "country_id": country_id,
        "policyengine_version": bundle_version,
        "model_package": _package_version(country_bundle["model_package"]),
        "data_package": data_package_payload,
        "default_dataset": default_dataset,
        "datasets": _dataset_path_references(datasets),
        "region_datasets": _region_dataset_templates(
            country_bundle.get("region_datasets", {})
        ),
        "certified_data_artifact": {
            "data_package": {
                "name": data_package_payload["name"],
                "version": data_package_payload["version"],
            },
            "dataset": default_dataset,
            "uri": _artifact_uri(default_artifact),
            "sha256": default_artifact.get("sha256"),
            "build_id": certification.get("data_build_id"),
        },
        "certification": {
            "compatibility_basis": _required_string(
                certification, "compatibility_basis"
            ),
            "data_build_id": certification.get("data_build_id"),
            "built_with_model_version": _package_pin_version(
                certification.get("built_with_model_package")
            ),
            "built_with_model_git_sha": _package_pin_git_sha(
                certification.get("built_with_model_package")
            ),
            "certified_for_model_version": _package_pin_version(
                certification.get("certified_for_model_package")
            ),
            "data_build_fingerprint": certification.get("data_build_fingerprint"),
            "certified_by": certification.get("certified_by"),
        },
    }


def _package_version(package: dict) -> dict:
    payload = {
        "name": _required_string(package, "name"),
        "version": _required_string(package, "version"),
    }
    if package.get("sha256"):
        payload["sha256"] = package["sha256"]
    if package.get("wheel_url"):
        payload["wheel_url"] = package["wheel_url"]
    return payload


def _dataset_path_references(datasets: dict) -> dict:
    path_references = {}
    for dataset, artifact in sorted(datasets.items()):
        if not isinstance(dataset, str) or not isinstance(artifact, dict):
            raise BundleImportError(
                "Country bundle datasets must map names to objects."
            )
        payload = {"path": _required_string(artifact, "path")}
        if artifact.get("revision"):
            payload["revision"] = artifact["revision"]
        if artifact.get("sha256"):
            payload["sha256"] = artifact["sha256"]
        if artifact.get("metadata_sha256"):
            payload["metadata_sha256"] = artifact["metadata_sha256"]
        path_references[dataset] = payload
    return path_references


def _region_dataset_templates(region_datasets: dict) -> dict:
    templates = {}
    if not isinstance(region_datasets, dict):
        raise BundleImportError("Country bundle region_datasets must be an object.")
    for region, template in sorted(region_datasets.items()):
        if not isinstance(region, str) or not isinstance(template, dict):
            raise BundleImportError(
                "Country bundle region_datasets must map names to objects."
            )
        if "path_template" in template:
            templates[region] = {"path_template": template["path_template"]}
    return templates


def _artifact_uri(artifact: dict) -> str:
    uri = artifact.get("uri")
    if isinstance(uri, str) and uri:
        return uri
    repo_id = _required_string(artifact, "repo_id")
    path = _required_string(artifact, "path")
    revision = _required_string(artifact, "revision")
    return f"hf://{repo_id}/{path}@{revision}"


def _package_pin_version(package: Any) -> Optional[str]:
    if isinstance(package, dict):
        version = package.get("version")
        if isinstance(version, str):
            return version
    return None


def _package_pin_git_sha(package: Any) -> Optional[str]:
    if isinstance(package, dict):
        git_sha = package.get("git_sha")
        if isinstance(git_sha, str):
            return git_sha
    return None


def _update_optional_dependency_pins(*, pyproject_path: Path, bundle: dict) -> None:
    packages = _required_dict(bundle, "packages")
    core_version = _required_string(
        _required_dict(packages, "policyengine-core"), "version"
    )
    replacements = {"policyengine_core": core_version}
    for package_name in COUNTRY_OPTIONAL_DEPENDENCIES.values():
        package = _required_dict(packages, package_name)
        replacements[package_name] = _required_string(package, "version")

    text = pyproject_path.read_text()
    text = _replace_optional_dependency_section(
        text,
        "uk",
        [
            f"policyengine_core=={core_version}",
            f"policyengine-uk=={replacements['policyengine-uk']}",
        ],
    )
    text = _replace_optional_dependency_section(
        text,
        "us",
        [
            f"policyengine_core=={core_version}",
            f"policyengine-us=={replacements['policyengine-us']}",
        ],
    )
    text = _replace_dependency_in_section(
        text, "dev", "policyengine_core", core_version
    )
    text = _replace_dependency_in_section(
        text,
        "dev",
        "policyengine-uk",
        replacements["policyengine-uk"],
    )
    text = _replace_dependency_in_section(
        text,
        "dev",
        "policyengine-us",
        replacements["policyengine-us"],
    )
    pyproject_path.write_text(text)


def _replace_optional_dependency_section(
    text: str,
    section_name: str,
    dependencies: list[str],
) -> str:
    section_start = text.find(f"{section_name} = [")
    if section_start == -1:
        raise BundleImportError(
            f"pyproject optional dependency missing: {section_name}"
        )
    content_start = text.find("\n", section_start)
    if content_start == -1:
        raise BundleImportError(f"Malformed pyproject section: {section_name}")
    content_end = text.find("\n]", content_start)
    if content_end == -1:
        raise BundleImportError(f"Malformed pyproject section: {section_name}")
    replacement = "\n".join(f'    "{dependency}",' for dependency in dependencies)
    return f"{text[: content_start + 1]}{replacement}{text[content_end:]}"


def _replace_dependency_in_section(
    text: str,
    section_name: str,
    package_name: str,
    version: str,
) -> str:
    section_start = text.find(f"{section_name} = [")
    if section_start == -1:
        raise BundleImportError(
            f"pyproject optional dependency missing: {section_name}"
        )
    content_start = text.find("\n", section_start)
    content_end = text.find("\n]", content_start)
    if content_start == -1 or content_end == -1:
        raise BundleImportError(f"Malformed pyproject section: {section_name}")

    lines = text[content_start + 1 : content_end].splitlines()
    updated_lines = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f'"{package_name}==') or stripped.startswith(
            f'"{package_name}>='
        ):
            updated_lines.append(f'    "{package_name}=={version}",')
            replaced = True
        else:
            updated_lines.append(line)
    if not replaced:
        raise BundleImportError(
            f"pyproject optional dependency {section_name} is missing {package_name}."
        )
    replacement = "\n".join(updated_lines)
    return f"{text[: content_start + 1]}{replacement}{text[content_end:]}"


def _write_changelog_fragment(
    *,
    changelog_dir: Path,
    version: str,
    bundle: dict,
) -> Path:
    packages = _required_dict(bundle, "packages")
    core_version = _required_string(
        _required_dict(packages, "policyengine-core"), "version"
    )
    uk_version = _required_string(
        _required_dict(packages, "policyengine-uk"), "version"
    )
    us_version = _required_string(
        _required_dict(packages, "policyengine-us"), "version"
    )
    changelog_dir.mkdir(parents=True, exist_ok=True)
    path = changelog_dir / f"policyengine-bundle-{version}.changed.md"
    path.write_text(
        f"Vend PolicyEngine bundle {version} with policyengine-core "
        f"{core_version}, policyengine-uk {uk_version}, and policyengine-us "
        f"{us_version}.\n"
    )
    return path


def _release_asset_names(version: str) -> tuple[str, str, str]:
    archive_name = f"policyengine-bundle-{version}.tar.gz"
    return archive_name, f"{archive_name}.sha256", f"policyengine-bundle-{version}.json"


def _read_checksum_file(path: Path, archive_name: str) -> str:
    parts = path.read_text().strip().split()
    if len(parts) != 2 or parts[1] != archive_name:
        raise BundleImportError(f"Malformed checksum file: {path}")
    return parts[0]


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_json(path: Path) -> dict:
    try:
        with path.open() as file:
            payload = json.load(file)
    except (OSError, ValueError) as exc:
        raise BundleImportError(f"Could not load JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BundleImportError(f"Expected JSON object in {path}.")
    return payload


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _required_dict(payload: dict, key: str) -> dict:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise BundleImportError(f"Expected object at {key}.")
    return value


def _required_string(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise BundleImportError(f"Expected non-empty string at {key}.")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
