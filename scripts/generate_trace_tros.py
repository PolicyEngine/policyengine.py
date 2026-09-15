"""Regenerate bundled TRACE TRO artifacts for every certified bundle country.

Writes ``data/bundle/{country}.trace.tro.jsonld`` for each country whose
certified data release ships in the bundle manifest. Run this before
releasing a new ``policyengine.py`` version so the packaged TRO
matches the pinned bundle. The richer data release manifest is included
when available; otherwise the TRO still binds the certified dataset
sha256 and URI pinned in the bundle manifest.

Public release workflows use ``strict=True``: complete manifests must match
the hash and URI in the reviewed sidecars, and all builder inputs must already
be pinned. Preparing a newly certified bundle remains a separate local step.
"""

from __future__ import annotations

import json
import sys
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator
from release_lock import PYPI, load_toml, validate_registry_artifacts

from policyengine.provenance.certification import validate_release_manifest
from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    DataReleaseManifest,
    DataReleaseManifestUnavailableError,
    get_data_release_manifest,
    get_release_manifest,
    https_release_manifest_uri,
)
from policyengine.provenance.trace import (
    build_trace_tro_from_release_bundle,
    serialize_trace_tro,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_MANIFEST = (
    REPO_ROOT / "src" / "policyengine" / "data" / "bundle" / "manifest.json"
)
BUNDLE_TRO_DIR = REPO_ROOT / "src" / "policyengine" / "data" / "bundle"
BUNDLE_LOCK = REPO_ROOT / "uv.lock"


def regenerate_all(
    *, strict: bool = False
) -> tuple[list[Path], list[tuple[str, Path, str]]]:
    written: list[Path] = []
    regressions: list[tuple[str, Path, str]] = []
    payloads = generated_tros(strict=strict)
    BUNDLE_TRO_DIR.mkdir(parents=True, exist_ok=True)
    for tro_path, payload in payloads:
        tro_path.write_bytes(payload)
        written.append(tro_path)
    return written, regressions


def _validate_reviewed_inputs(
    country: CountryReleaseManifest,
    data: DataReleaseManifest,
    tro_path: Path,
) -> None:
    """Authenticate full release inputs without downloading the dataset again."""
    prefix = f"{country.country_id}: strict TRACE release"
    revision = country.data_package.release_manifest_revision
    if not revision or revision.lower() in {"main", "master", "latest"}:
        raise ValueError(f"{prefix} requires a pinned data release manifest revision")
    if not country.model_package.sha256 or not country.model_package.wheel_url:
        raise ValueError(f"{prefix} requires a pinned model wheel hash and URL")
    if (
        country.certification is None
        or country.certification.certified_for_model_version
        != country.model_package.version
    ):
        raise ValueError(f"{prefix} requires certification for the pinned model")
    validate_release_manifest(
        data, country.model_package.name, country.model_package.version
    )
    certified = country.certified_data_artifact
    artifact = data.artifacts.get(certified.dataset) if certified else None
    if (
        certified is None
        or artifact is None
        or not certified.sha256
        or artifact.sha256 != certified.sha256
    ):
        raise ValueError(
            f"{prefix} requires the certified dataset and matching hash in the full data release manifest"
        )

    # The committed TRO is the reviewed source pin. A changed data release must
    # first be certified and its full sidecar prepared/reviewed before release;
    # Versioning may change wrapper versions, but never substitute remote bytes.
    artifact_id = "composition/1/artifact/data_release_manifest"
    try:
        tro = json.loads(tro_path.read_bytes())["@graph"][0]
        pins = [
            item["trov:sha256"]
            for item in tro["trov:hasComposition"]["trov:hasArtifact"]
            if item["@id"] == artifact_id
        ]
        locations = [
            item["trov:hasLocation"]
            for arrangement in tro["trov:hasArrangement"]
            for item in arrangement["trov:hasArtifactLocation"]
            if item["trov:hasArtifact"]["@id"] == artifact_id
        ]
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            f"{prefix} requires a reviewed full sidecar at {tro_path}"
        ) from exc
    if not data.source_sha256 or pins != [data.source_sha256]:
        raise ValueError(
            f"{prefix}: reviewed data release manifest hash does not match fetched bytes"
        )
    if locations != [https_release_manifest_uri(country.data_package)]:
        raise ValueError(
            f"{prefix}: reviewed data release manifest URI does not match the bundle"
        )


def _validate_runtime_model(bundle: dict, country: CountryReleaseManifest) -> None:
    """Connect the certification to the package and wheel installed by the lock."""
    key = f"policyengine-{country.country_id}"
    component = bundle.get("packages", {}).get(key, {})
    model = country.model_package
    prefix = f"{country.country_id}: strict TRACE release"
    if (
        model.name != key
        or component.get("name") != model.name
        or component.get("version") != model.version
        or any(
            field in component and component[field] != getattr(model, field)
            for field in ("sha256", "wheel_url")
        )
    ):
        raise ValueError(
            f"{prefix}: runtime country model differs from the certified model"
        )
    try:
        locked = [
            package
            for package in load_toml(BUNDLE_LOCK).get("package", [])
            if package["name"] == model.name
        ]
    except (OSError, ValueError) as exc:
        raise ValueError(f"{prefix} requires the reviewed registry lock") from exc
    if (
        len(locked) != 1
        or locked[0]["version"] != model.version
        or locked[0].get("source") != {"registry": PYPI}
    ):
        raise ValueError(
            f"{prefix}: registry lock differs from the certified runtime model"
        )
    validate_registry_artifacts(locked[0])
    if {(wheel["url"], wheel["hash"]) for wheel in locked[0].get("wheels", [])} != {
        (model.wheel_url, f"sha256:{model.sha256}")
    }:
        raise ValueError(
            f"{prefix}: locked runtime wheel differs from the certified model wheel"
        )


def generated_tros(*, strict: bool = False) -> list[tuple[Path, bytes]]:
    """Prepare and schema-validate every serialized country TRO without writes."""
    payloads: list[tuple[Path, bytes]] = []
    bundle = json.loads(BUNDLE_MANIFEST.read_text())
    schema = json.loads(
        files("policyengine")
        .joinpath("data", "schemas", "trace_tro.schema.json")
        .read_text()
    )
    validator = Draft202012Validator(schema)
    if strict:
        expected = {
            country
            for country in ("us", "uk")
            if f"policyengine-{country}" in bundle.get("packages", {})
        }
        if not expected or expected - bundle.get("data_releases", {}).keys():
            raise ValueError(
                "Strict TRACE release requires a data release manifest for every bundled country model"
            )
    for country_id in sorted(bundle.get("data_releases", {})):
        tro_path = BUNDLE_TRO_DIR / f"{country_id}.trace.tro.jsonld"
        country_manifest = get_release_manifest(country_id)
        if strict:
            _validate_runtime_model(bundle, country_manifest)
        try:
            data_release_manifest = get_data_release_manifest(country_id)
        except DataReleaseManifestUnavailableError as exc:
            if strict:
                raise
            data_release_manifest = None
            print(
                f"warning: {country_id}: {exc}; writing limited TRO",
                file=sys.stderr,
            )
        if strict:
            _validate_reviewed_inputs(country_manifest, data_release_manifest, tro_path)
        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            data_release_manifest,
            certification=country_manifest.certification,
            model_wheel_sha256=country_manifest.model_package.sha256,
            model_wheel_url=country_manifest.model_package.wheel_url,
            emission_context={"pe:emittedIn": "repository-bundle"},
        )
        payload = serialize_trace_tro(tro)
        validator.validate(json.loads(payload))
        payloads.append((tro_path, payload))
    return payloads


def main() -> int:
    if not BUNDLE_MANIFEST.is_file():
        print(f"no bundle manifest at {BUNDLE_MANIFEST}", file=sys.stderr)
        return 1
    written, regressions = regenerate_all()
    for path in written:
        print(f"wrote {path}")
    for country_id, tro_path, reason in regressions:
        print(
            f"error: {country_id} already has {tro_path.name} but regeneration "
            f"failed: {reason}",
            file=sys.stderr,
        )
    if regressions:
        return 1
    if not written:
        print("no countries could be regenerated (all skipped)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
