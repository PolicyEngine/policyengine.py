"""Agent-safe orchestration for refreshing certified release bundles.

This module sits above :mod:`policyengine.provenance.bundle`. It resolves
target model/data versions, verifies the data release certifies the target
model, then delegates file mutation to ``refresh_release_bundle``.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, Sequence
from urllib.request import Request, urlopen

from policyengine.provenance.bundle import (
    MANIFEST_DIR,
    PYPROJECT,
    RefreshResult,
    _fetch_data_release_manifest,
    _pypi_wheel_metadata,
    _updated_release_manifest_path,
    refresh_release_bundle,
    regenerate_trace_tro,
)
from policyengine.provenance.manifest import CountryReleaseManifest, DataCertification

COUNTRIES = ("us", "uk")
PACKAGE_ROOTS = {
    "policyengine-us": "policyengine_us",
    "policyengine-uk": "policyengine_uk",
}


class _HashDigest(Protocol):
    def update(self, data: bytes, /) -> None: ...


@dataclass(frozen=True)
class CountryBundleUpdatePlan:
    """Resolved, certification-checked bundle target for one country."""

    country: str
    current_model_version: str
    target_model_version: str
    current_data_version: str
    target_data_version: str
    release_manifest_path: Optional[str]
    release_manifest_revision: Optional[str]
    compatibility_basis: str
    target_data_build_fingerprint: str
    data_source: str
    prevalidated_certification: Optional[DataCertification] = None

    def summary(self) -> str:
        return (
            f"{self.country}: model {self.current_model_version} -> "
            f"{self.target_model_version}; data {self.current_data_version} -> "
            f"{self.target_data_version}; basis={self.compatibility_basis}; "
            f"source={self.data_source}"
        )


@dataclass
class BundleUpdateOutcome:
    """Plans and refresh results from a bundle update run."""

    plans: list[CountryBundleUpdatePlan]
    results: list[RefreshResult]
    tro_paths: list[Path]

    def summary(self) -> str:
        lines = ["Resolved release bundle update:"]
        lines.extend(f"  {plan.summary()}" for plan in self.plans)
        if self.results:
            lines.append("")
            lines.extend(result.summary() for result in self.results)
        if self.tro_paths:
            lines.append("")
            lines.extend(f"TRACE TRO regenerated: {path}" for path in self.tro_paths)
        return "\n".join(lines)


def _ensure_source_checkout(manifest_dir: Path, pyproject_path: Path) -> None:
    if not pyproject_path.is_file():
        raise ValueError(
            "Release-bundle refresh requires a policyengine.py source checkout; "
            f"missing {pyproject_path}."
        )
    if not manifest_dir.is_dir():
        raise ValueError(
            "Release-bundle refresh requires a policyengine.py source checkout; "
            f"missing {manifest_dir}."
        )


def _load_release_manifest(
    country: str,
    *,
    manifest_dir: Path,
) -> CountryReleaseManifest:
    manifest_path = manifest_dir / f"{country}.json"
    if not manifest_path.is_file():
        raise ValueError(f"No bundled release manifest found for country {country!r}.")
    return CountryReleaseManifest.model_validate_json(manifest_path.read_text())


def _latest_pypi_version(package: str) -> str:
    url = f"https://pypi.org/pypi/{package}/json"
    with urlopen(Request(url, headers={"User-Agent": "policyengine.py"})) as f:
        payload = json.load(f)
    version = payload.get("info", {}).get("version")
    if not version:
        raise ValueError(f"Could not resolve latest PyPI version for {package}.")
    return version


def _download_bytes(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "policyengine.py"})) as f:
        return f.read()


def _string_tuple_constant(source: str, name: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    for node in tree.body:
        target_name = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                target_name = target.id
                value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value = node.value
        if target_name != name or value is None:
            continue
        literal = ast.literal_eval(value)
        if not isinstance(literal, (list, tuple)) or not all(
            isinstance(item, str) for item in literal
        ):
            raise ValueError(f"{name} in build_metadata.py must be a string list.")
        return tuple(literal)
    raise ValueError(f"build_metadata.py does not define {name}.")


def _wheel_data_build_fingerprint(package: str, wheel_url: str) -> str:
    package_root = PACKAGE_ROOTS.get(package)
    if package_root is None:
        raise ValueError(f"Unsupported country model package {package!r}.")

    wheel_bytes = _download_bytes(wheel_url)
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as wheel:
        metadata_path = f"{package_root}/build_metadata.py"
        try:
            metadata_source = wheel.read(metadata_path).decode("utf-8")
        except KeyError as exc:
            raise ValueError(
                f"Wheel for {package} does not include {metadata_path}."
            ) from exc
        surface = _string_tuple_constant(metadata_source, "DATA_BUILD_SURFACE")
        names = {
            name: info
            for name, info in ((info.filename, info) for info in wheel.infolist())
            if not info.is_dir()
        }
        digest = hashlib.sha256()
        for relative_path in surface:
            file_name = f"{package_root}/{relative_path}"
            if file_name in names:
                _hash_wheel_member(
                    digest,
                    relative_path=relative_path,
                    wheel=wheel,
                    member=file_name,
                )
                continue
            prefix = f"{file_name.rstrip('/')}/"
            children = [
                name
                for name in names
                if name.startswith(prefix)
                and "__pycache__" not in name.split("/")
                and not name.endswith((".pyc", ".pyo"))
            ]
            if not children:
                continue
            for child in sorted(children):
                _hash_wheel_member(
                    digest,
                    relative_path=child[len(package_root) + 1 :],
                    wheel=wheel,
                    member=child,
                )
    return f"sha256:{digest.hexdigest()}"


def _hash_wheel_member(
    digest: _HashDigest,
    *,
    relative_path: str,
    wheel: zipfile.ZipFile,
    member: str,
) -> None:
    digest.update(relative_path.encode("utf-8"))
    digest.update(b"\0")
    digest.update(wheel.read(member))
    digest.update(b"\0")


def _target_model_fingerprint(package: str, version: str) -> str:
    wheel = _pypi_wheel_metadata(package, version)
    return _wheel_data_build_fingerprint(package, wheel["url"])


def _release_manifest_data_version(release_manifest_json: dict) -> str:
    version = release_manifest_json.get("data_package", {}).get("version")
    if not version:
        raise ValueError("Data release manifest does not declare data_package.version.")
    return version


def _certification_basis(
    *,
    country: str,
    model_package: str,
    target_model_version: str,
    target_data_build_fingerprint: str,
    release_manifest_json: dict,
) -> str:
    build = release_manifest_json.get("build") or {}
    built_with_model = build.get("built_with_model_package") or {}
    built_with_name = built_with_model.get("name")
    if built_with_name is not None and built_with_name != model_package:
        raise ValueError(
            f"{country}: data release was built with {built_with_name}, "
            f"not {model_package}."
        )

    built_with_version = built_with_model.get("version")
    if built_with_version == target_model_version:
        return "exact_build_model_version"

    data_build_fingerprint = built_with_model.get("data_build_fingerprint")
    if (
        data_build_fingerprint is not None
        and data_build_fingerprint == target_data_build_fingerprint
    ):
        return "matching_data_build_fingerprint"

    raise ValueError(
        f"{country}: data release does not certify {model_package} "
        f"{target_model_version}; publish a new country data release first."
    )


def _current_data_certification(
    *,
    country: str,
    current: CountryReleaseManifest,
    target_model_version: str,
    target_data_build_fingerprint: str,
) -> DataCertification:
    certification = current.certification
    if certification is None:
        raise ValueError(
            f"{country}: current bundle has no certification metadata; "
            "cannot reuse current data."
        )
    if certification.certified_for_model_version == target_model_version:
        return certification
    if (
        certification.data_build_fingerprint is not None
        and certification.data_build_fingerprint == target_data_build_fingerprint
    ):
        return DataCertification(
            compatibility_basis="matching_data_build_fingerprint",
            certified_for_model_version=target_model_version,
            data_build_id=certification.data_build_id,
            built_with_model_version=certification.built_with_model_version,
            built_with_model_git_sha=certification.built_with_model_git_sha,
            data_build_fingerprint=certification.data_build_fingerprint,
            certified_by=certification.certified_by,
        )
    raise ValueError(
        f"{country}: current data release does not certify "
        f"{current.model_package.name} {target_model_version}; publish a new "
        "country data release first."
    )


def _fetch_release_manifest_for_plan(
    *,
    current: CountryReleaseManifest,
    data_version: Optional[str],
    release_manifest_path: Optional[str],
    release_manifest_revision: Optional[str],
):
    path = release_manifest_path or current.data_package.release_manifest_path
    if path is None:
        return None, None, None

    if data_version is not None:
        target_path = release_manifest_path or _updated_release_manifest_path(
            current_path=path,
            old_data=current.data_package.version,
            new_data=data_version,
        )
        fetch = _fetch_data_release_manifest(
            repo_id=current.data_package.repo_id,
            release_manifest_path=target_path,
            revision=release_manifest_revision or data_version,
            allow_main_fallback=release_manifest_revision is None,
        )
        return fetch, target_path, release_manifest_revision

    fetch = _fetch_data_release_manifest(
        repo_id=current.data_package.repo_id,
        release_manifest_path=path,
        revision=release_manifest_revision or "main",
        allow_main_fallback=False,
    )
    return fetch, path, release_manifest_revision


def _resolve_country_plan(
    country: str,
    *,
    model_version: Optional[str],
    data_version: Optional[str],
    release_manifest_path: Optional[str],
    release_manifest_revision: Optional[str],
    manifest_dir: Path,
) -> CountryBundleUpdatePlan:
    current = _load_release_manifest(country, manifest_dir=manifest_dir)
    target_model_version = model_version or _latest_pypi_version(
        current.model_package.name
    )
    target_fingerprint = _target_model_fingerprint(
        current.model_package.name,
        target_model_version,
    )
    fetch, target_path, explicit_revision = _fetch_release_manifest_for_plan(
        current=current,
        data_version=data_version,
        release_manifest_path=release_manifest_path,
        release_manifest_revision=release_manifest_revision,
    )

    if fetch is not None:
        fetched_data_version = _release_manifest_data_version(fetch.payload)
        if data_version is not None and fetched_data_version != data_version:
            raise ValueError(
                f"{country}: data release manifest declares "
                f"{fetched_data_version}, expected {data_version}."
            )
        basis = _certification_basis(
            country=country,
            model_package=current.model_package.name,
            target_model_version=target_model_version,
            target_data_build_fingerprint=target_fingerprint,
            release_manifest_json=fetch.payload,
        )
        return CountryBundleUpdatePlan(
            country=country,
            current_model_version=current.model_package.version,
            target_model_version=target_model_version,
            current_data_version=current.data_package.version,
            target_data_version=fetched_data_version,
            release_manifest_path=target_path,
            release_manifest_revision=fetch.repo_commit or explicit_revision,
            compatibility_basis=basis,
            target_data_build_fingerprint=target_fingerprint,
            data_source="data_release_manifest",
        )

    if data_version is not None:
        raise ValueError(
            f"{country}: could not fetch data release manifest for "
            f"{current.data_package.name} {data_version}."
        )

    prevalidated_certification = _current_data_certification(
        country=country,
        current=current,
        target_model_version=target_model_version,
        target_data_build_fingerprint=target_fingerprint,
    )
    return CountryBundleUpdatePlan(
        country=country,
        current_model_version=current.model_package.version,
        target_model_version=target_model_version,
        current_data_version=current.data_package.version,
        target_data_version=current.data_package.version,
        release_manifest_path=target_path or current.data_package.release_manifest_path,
        release_manifest_revision=(
            release_manifest_revision or current.data_package.release_manifest_revision
        ),
        compatibility_basis=prevalidated_certification.compatibility_basis,
        target_data_build_fingerprint=target_fingerprint,
        data_source="current_bundle_certification",
        prevalidated_certification=prevalidated_certification,
    )


def _selected_countries(country: str) -> tuple[str, ...]:
    if country == "all":
        return COUNTRIES
    if country not in COUNTRIES:
        raise ValueError("country must be one of: us, uk, all")
    return (country,)


def _reject_common_all_options(
    *,
    country: str,
    model_version: Optional[str],
    data_version: Optional[str],
    release_manifest_path: Optional[str],
    release_manifest_revision: Optional[str],
) -> None:
    if country != "all":
        return
    common_options = {
        "--model-version": model_version,
        "--data-version": data_version,
        "--release-manifest-path": release_manifest_path,
        "--release-manifest-revision": release_manifest_revision,
    }
    used = [name for name, value in common_options.items() if value is not None]
    if used:
        raise ValueError(
            "--country all cannot use common explicit target flags "
            f"{', '.join(used)}; use the matching --us-* and --uk-* flags instead."
        )


def _country_option(
    selected: str,
    country: str,
    *,
    common: Optional[str],
    us: Optional[str],
    uk: Optional[str],
) -> Optional[str]:
    if selected == "all":
        return {"us": us, "uk": uk}[country] or common
    return common or {"us": us, "uk": uk}[country]


def plan_release_bundle_updates(
    *,
    country: str,
    model_version: Optional[str] = None,
    data_version: Optional[str] = None,
    release_manifest_path: Optional[str] = None,
    release_manifest_revision: Optional[str] = None,
    us_model_version: Optional[str] = None,
    uk_model_version: Optional[str] = None,
    us_data_version: Optional[str] = None,
    uk_data_version: Optional[str] = None,
    us_release_manifest_path: Optional[str] = None,
    uk_release_manifest_path: Optional[str] = None,
    us_release_manifest_revision: Optional[str] = None,
    uk_release_manifest_revision: Optional[str] = None,
    manifest_dir: Path = MANIFEST_DIR,
    pyproject_path: Path = PYPROJECT,
) -> list[CountryBundleUpdatePlan]:
    """Resolve and preflight bundle refresh targets without writing files."""

    _ensure_source_checkout(manifest_dir, pyproject_path)
    _reject_common_all_options(
        country=country,
        model_version=model_version,
        data_version=data_version,
        release_manifest_path=release_manifest_path,
        release_manifest_revision=release_manifest_revision,
    )
    countries = _selected_countries(country)
    plans: list[CountryBundleUpdatePlan] = []
    for country_id in countries:
        plans.append(
            _resolve_country_plan(
                country_id,
                model_version=_country_option(
                    country,
                    country_id,
                    common=model_version,
                    us=us_model_version,
                    uk=uk_model_version,
                ),
                data_version=_country_option(
                    country,
                    country_id,
                    common=data_version,
                    us=us_data_version,
                    uk=uk_data_version,
                ),
                release_manifest_path=_country_option(
                    country,
                    country_id,
                    common=release_manifest_path,
                    us=us_release_manifest_path,
                    uk=uk_release_manifest_path,
                ),
                release_manifest_revision=_country_option(
                    country,
                    country_id,
                    common=release_manifest_revision,
                    us=us_release_manifest_revision,
                    uk=uk_release_manifest_revision,
                ),
                manifest_dir=manifest_dir,
            )
        )
    return plans


def _snapshot_paths(
    plans: Sequence[CountryBundleUpdatePlan],
    *,
    manifest_dir: Path,
    pyproject_path: Path,
) -> dict[Path, Optional[bytes]]:
    paths = {pyproject_path}
    for plan in plans:
        paths.add(manifest_dir / f"{plan.country}.json")
        paths.add(manifest_dir / f"{plan.country}.trace.tro.jsonld")
    return {path: path.read_bytes() if path.exists() else None for path in paths}


def _restore_snapshot(snapshot: dict[Path, Optional[bytes]]) -> None:
    for path, content in snapshot.items():
        if content is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def refresh_release_bundles(
    *,
    country: str,
    model_version: Optional[str] = None,
    data_version: Optional[str] = None,
    release_manifest_path: Optional[str] = None,
    release_manifest_revision: Optional[str] = None,
    us_model_version: Optional[str] = None,
    uk_model_version: Optional[str] = None,
    us_data_version: Optional[str] = None,
    uk_data_version: Optional[str] = None,
    us_release_manifest_path: Optional[str] = None,
    uk_release_manifest_path: Optional[str] = None,
    us_release_manifest_revision: Optional[str] = None,
    uk_release_manifest_revision: Optional[str] = None,
    manifest_dir: Path = MANIFEST_DIR,
    pyproject_path: Path = PYPROJECT,
    regenerate_tros: bool = True,
) -> BundleUpdateOutcome:
    """Preflight and refresh one or more release-bundle segments."""

    plans = plan_release_bundle_updates(
        country=country,
        model_version=model_version,
        data_version=data_version,
        release_manifest_path=release_manifest_path,
        release_manifest_revision=release_manifest_revision,
        us_model_version=us_model_version,
        uk_model_version=uk_model_version,
        us_data_version=us_data_version,
        uk_data_version=uk_data_version,
        us_release_manifest_path=us_release_manifest_path,
        uk_release_manifest_path=uk_release_manifest_path,
        us_release_manifest_revision=us_release_manifest_revision,
        uk_release_manifest_revision=uk_release_manifest_revision,
        manifest_dir=manifest_dir,
        pyproject_path=pyproject_path,
    )
    snapshot = _snapshot_paths(
        plans,
        manifest_dir=manifest_dir,
        pyproject_path=pyproject_path,
    )
    results: list[RefreshResult] = []
    tro_paths: list[Path] = []
    try:
        for plan in plans:
            results.append(
                refresh_release_bundle(
                    country=plan.country,
                    model_version=plan.target_model_version,
                    data_version=plan.target_data_version,
                    release_manifest_path=(
                        None
                        if plan.prevalidated_certification is not None
                        else plan.release_manifest_path
                    ),
                    release_manifest_revision=(
                        None
                        if plan.prevalidated_certification is not None
                        else plan.release_manifest_revision
                    ),
                    prevalidated_certification=plan.prevalidated_certification,
                    manifest_dir=manifest_dir,
                    pyproject_path=pyproject_path,
                )
            )
            if regenerate_tros:
                tro_paths.append(
                    regenerate_trace_tro(plan.country, manifest_dir=manifest_dir)
                )
    except Exception:
        _restore_snapshot(snapshot)
        raise

    return BundleUpdateOutcome(plans=plans, results=results, tro_paths=tro_paths)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="refresh_release_bundles",
        description=(
            "Refresh certified policyengine.py release-bundle segments. "
            "The command fails unless each target country data release certifies "
            "the target model by exact build version or data_build_fingerprint."
        ),
    )
    parser.add_argument("--country", required=True, choices=("us", "uk", "all"))
    parser.add_argument("--model-version")
    parser.add_argument("--data-version")
    parser.add_argument("--release-manifest-path")
    parser.add_argument("--release-manifest-revision")
    parser.add_argument("--us-model-version")
    parser.add_argument("--uk-model-version")
    parser.add_argument("--us-data-version")
    parser.add_argument("--uk-data-version")
    parser.add_argument("--us-release-manifest-path")
    parser.add_argument("--uk-release-manifest-path")
    parser.add_argument("--us-release-manifest-revision")
    parser.add_argument("--uk-release-manifest-revision")
    parser.epilog = (
        "Examples: "
        "python scripts/refresh_release_bundles.py --country us; "
        "python scripts/refresh_release_bundles.py --country all "
        "--us-model-version 1.715.2 --uk-model-version 2.89.0"
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        outcome = refresh_release_bundles(
            country=args.country,
            model_version=args.model_version,
            data_version=args.data_version,
            release_manifest_path=args.release_manifest_path,
            release_manifest_revision=args.release_manifest_revision,
            us_model_version=args.us_model_version,
            uk_model_version=args.uk_model_version,
            us_data_version=args.us_data_version,
            uk_data_version=args.uk_data_version,
            us_release_manifest_path=args.us_release_manifest_path,
            uk_release_manifest_path=args.uk_release_manifest_path,
            us_release_manifest_revision=args.us_release_manifest_revision,
            uk_release_manifest_revision=args.uk_release_manifest_revision,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(outcome.summary())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
