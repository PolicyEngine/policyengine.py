"""Validate a bundled country release manifest after a bundle refresh.

This is intentionally narrower than the full pytest modules. It checks the
user-facing bundle metadata, the country model wrapper's exposed bundle, and the
TRACE TRO sidecar without running representative-data calculations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Any, Optional

os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")

from jsonschema import Draft202012Validator

from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    get_release_manifest,
)
from policyengine.provenance.trace import canonical_json_bytes

COUNTRIES = ("us", "uk")
EXPECTED_TRO_ARTIFACTS = {
    "bundle_manifest",
    "data_release_manifest",
    "dataset",
    "model_wheel",
}
VALID_COMPATIBILITY_BASES = {
    "exact_build_model_version",
    "matching_data_build_fingerprint",
    "legacy_compatible_model_package",
}
ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "src" / "policyengine" / "data" / "release_manifests"
TRACE_SCHEMA_PATH = (
    ROOT / "src" / "policyengine" / "data" / "schemas" / "trace_tro.schema.json"
)


def _sha256(value: Optional[str]) -> bool:
    if value is None or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _hf_revision(uri: str) -> Optional[str]:
    if not uri.startswith("hf://") or "@" not in uri:
        return None
    return uri.rsplit("@", 1)[1] or None


def _short_artifact_id(artifact_id: str) -> str:
    return artifact_id.rsplit("/", 1)[-1]


def _artifact_by_id(tro: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
    return {_short_artifact_id(artifact["@id"]): artifact for artifact in artifacts}


def _location_by_id(tro: dict[str, Any]) -> dict[str, dict[str, Any]]:
    locations = tro["@graph"][0]["trov:hasArrangement"][0]["trov:hasArtifactLocation"]
    return {_short_artifact_id(location["@id"]): location for location in locations}


def _performance(tro: dict[str, Any]) -> dict[str, Any]:
    return tro["@graph"][0]["trov:hasPerformance"]


class BundleValidator:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        if not condition:
            self.failures.append(message)

    def check_equal(self, label: str, actual: Any, expected: Any) -> None:
        self.check(
            actual == expected, f"{label}: expected {expected!r}, got {actual!r}"
        )

    def validate_manifest(
        self,
        manifest: CountryReleaseManifest,
        *,
        expected_model_version: Optional[str],
        expected_data_version: Optional[str],
        expected_built_with_model_version: Optional[str],
        expected_compatibility_basis: Optional[str],
    ) -> None:
        country = manifest.country_id
        model_name = f"policyengine-{country}"
        data_name = f"policyengine-{country}-data"
        artifact = manifest.certified_data_artifact
        certification = manifest.certification

        self.check(manifest.bundle_id is not None, "bundle_id is missing")
        if manifest.bundle_id is not None:
            self.check_equal(
                "bundle_id country prefix",
                manifest.bundle_id.split("-", 1)[0],
                country,
            )
        self.check_equal("model package name", manifest.model_package.name, model_name)
        self.check_equal("data package name", manifest.data_package.name, data_name)
        self.check(
            _sha256(manifest.model_package.sha256),
            "model wheel sha256 missing or invalid",
        )
        self.check(
            bool(manifest.model_package.wheel_url),
            "model wheel URL missing from manifest",
        )
        self.check(
            bool(manifest.data_package.release_manifest_revision),
            "data release manifest revision must be pinned to an immutable revision",
        )

        if expected_model_version is not None:
            self.check_equal(
                "model package version",
                manifest.model_package.version,
                expected_model_version,
            )
        if expected_data_version is not None:
            self.check_equal(
                "data package version",
                manifest.data_package.version,
                expected_data_version,
            )

        self.check(artifact is not None, "certified_data_artifact is missing")
        self.check(certification is not None, "certification is missing")
        if artifact is None or certification is None:
            return

        if artifact.data_package is not None:
            self.check_equal(
                "certified artifact data package name",
                artifact.data_package.name,
                manifest.data_package.name,
            )
            self.check_equal(
                "certified artifact data package version",
                artifact.data_package.version,
                manifest.data_package.version,
            )

        self.check_equal(
            "default dataset URI",
            manifest.default_dataset_uri,
            artifact.uri,
        )
        self.check(
            _sha256(artifact.sha256), "certified dataset sha256 missing or invalid"
        )
        self.check_equal(
            "certification data build id",
            certification.data_build_id,
            artifact.build_id,
        )
        self.check_equal(
            "certified model version",
            certification.certified_for_model_version,
            manifest.model_package.version,
        )
        self.check(
            certification.compatibility_basis in VALID_COMPATIBILITY_BASES,
            f"unexpected compatibility basis {certification.compatibility_basis!r}",
        )
        self.check(
            certification.built_with_model_version is not None,
            "built_with_model_version is missing",
        )
        self.check(
            certification.data_build_fingerprint is not None,
            "data_build_fingerprint is missing",
        )
        if certification.compatibility_basis == "exact_build_model_version":
            self.check_equal(
                "exact-build certified model version",
                certification.certified_for_model_version,
                certification.built_with_model_version,
            )
        if (
            certification.built_with_model_version != manifest.model_package.version
            and certification.compatibility_basis == "exact_build_model_version"
        ):
            self.failures.append(
                "compatibility_basis cannot be exact_build_model_version when the "
                "data was built with a different model version"
            )
        if expected_built_with_model_version is not None:
            self.check_equal(
                "built-with model version",
                certification.built_with_model_version,
                expected_built_with_model_version,
            )
        if expected_compatibility_basis is not None:
            self.check_equal(
                "compatibility basis",
                certification.compatibility_basis,
                expected_compatibility_basis,
            )

        revision = _hf_revision(artifact.uri)
        self.check(
            revision is not None,
            "certified dataset URI must be an hf:// URI with @revision",
        )
        if manifest.data_package.release_manifest_revision is not None:
            self.check_equal(
                "certified dataset revision",
                revision,
                manifest.data_package.release_manifest_revision,
            )

        dataset_ref = manifest.datasets.get(manifest.default_dataset)
        self.check(dataset_ref is not None, "default dataset is missing from datasets")
        if dataset_ref is not None:
            self.check_equal(
                "default dataset sha256",
                dataset_ref.sha256,
                artifact.sha256,
            )

    def validate_model_wrapper(
        self, country: str, manifest: CountryReleaseManifest
    ) -> None:
        module = import_module(f"policyengine.tax_benefit_models.{country}")
        model_version = getattr(module, f"{country}_latest")
        certification = manifest.certification
        artifact = manifest.certified_data_artifact

        self.check_equal(
            "wrapper model version",
            model_version.model_package.version,
            manifest.model_package.version,
        )
        self.check_equal(
            "wrapper data version",
            model_version.data_package.version,
            manifest.data_package.version,
        )
        self.check_equal(
            "wrapper default dataset URI",
            model_version.default_dataset_uri,
            manifest.default_dataset_uri,
        )
        self.check_equal(
            "wrapper release manifest country",
            model_version.release_manifest.country_id,
            country,
        )

        bundle = model_version.release_bundle
        self.check_equal(
            "release bundle model version",
            bundle["model_version"],
            manifest.model_package.version,
        )
        self.check_equal(
            "release bundle data version",
            bundle["data_version"],
            manifest.data_package.version,
        )
        if certification is not None:
            self.check_equal(
                "release bundle compatibility basis",
                bundle["compatibility_basis"],
                certification.compatibility_basis,
            )
            self.check_equal(
                "release bundle data build model version",
                bundle["data_build_model_version"],
                certification.built_with_model_version,
            )
            self.check_equal(
                "release bundle data build fingerprint",
                bundle["data_build_fingerprint"],
                certification.data_build_fingerprint,
            )
        if artifact is not None:
            self.check_equal(
                "release bundle certified data build id",
                bundle["certified_data_build_id"],
                artifact.build_id,
            )

    def validate_tro(
        self,
        country: str,
        manifest: CountryReleaseManifest,
        *,
        allow_limited_tro: bool,
    ) -> None:
        tro_path = MANIFEST_DIR / f"{country}.trace.tro.jsonld"
        self.check(tro_path.is_file(), f"{tro_path} is missing")
        if not tro_path.is_file():
            return

        tro = json.loads(tro_path.read_text())
        schema = json.loads(TRACE_SCHEMA_PATH.read_text())
        errors = sorted(Draft202012Validator(schema).iter_errors(tro), key=str)
        for error in errors:
            path = ".".join(str(part) for part in error.absolute_path)
            self.failures.append(
                f"TRO schema error at {path or '<root>'}: {error.message}"
            )

        artifacts = _artifact_by_id(tro)
        locations = _location_by_id(tro)
        artifact_ids = set(artifacts)
        required_artifacts = set(EXPECTED_TRO_ARTIFACTS)
        if allow_limited_tro:
            required_artifacts.remove("data_release_manifest")
        self.check(
            required_artifacts.issubset(artifact_ids),
            f"TRO artifacts missing: {sorted(required_artifacts - artifact_ids)}",
        )
        if not allow_limited_tro:
            self.check(
                "data_release_manifest" in artifact_ids,
                "TRO must include the data_release_manifest artifact",
            )

        performance = _performance(tro)
        certification = manifest.certification
        artifact = manifest.certified_data_artifact
        self.check_equal(
            "TRO certified model version",
            performance.get("pe:certifiedForModelVersion"),
            manifest.model_package.version,
        )
        if certification is not None:
            self.check_equal(
                "TRO built-with model version",
                performance.get("pe:builtWithModelVersion"),
                certification.built_with_model_version,
            )
            self.check_equal(
                "TRO compatibility basis",
                performance.get("pe:compatibilityBasis"),
                certification.compatibility_basis,
            )
            self.check_equal(
                "TRO data build fingerprint",
                performance.get("pe:dataBuildFingerprint"),
                certification.data_build_fingerprint,
            )
            self.check_equal(
                "TRO data build id",
                performance.get("pe:dataBuildId"),
                certification.data_build_id,
            )
        if not allow_limited_tro:
            self.check(
                performance.get("pe:dataReleaseManifestStatus") != "unavailable",
                "TRO says the data release manifest is unavailable",
            )

        bundle_artifact = artifacts.get("bundle_manifest")
        if bundle_artifact is not None:
            expected_manifest_hash = canonical_json_bytes(
                manifest.model_dump(mode="json")
            )
            self.check_equal(
                "TRO bundle manifest sha256",
                bundle_artifact.get("trov:sha256"),
                hashlib.sha256(expected_manifest_hash).hexdigest(),
            )
        dataset_artifact = artifacts.get("dataset")
        if dataset_artifact is not None and artifact is not None:
            self.check_equal(
                "TRO dataset sha256",
                dataset_artifact.get("trov:sha256"),
                artifact.sha256,
            )
        model_wheel = artifacts.get("model_wheel")
        if model_wheel is not None:
            self.check_equal(
                "TRO model wheel sha256",
                model_wheel.get("trov:sha256"),
                manifest.model_package.sha256,
            )
            self.check(
                f"{manifest.model_package.name}=={manifest.model_package.version}"
                in model_wheel.get("schema:name", ""),
                "TRO model wheel name does not match the manifest model package",
            )
        model_wheel_location = locations.get("model_wheel")
        if model_wheel_location is not None:
            self.check_equal(
                "TRO model wheel location",
                model_wheel_location.get("trov:hasLocation"),
                manifest.model_package.wheel_url,
            )


def parse_args(argv: Optional[list[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", required=True, choices=COUNTRIES)
    parser.add_argument("--expected-model-version")
    parser.add_argument("--expected-data-version")
    parser.add_argument("--expected-built-with-model-version")
    parser.add_argument(
        "--expected-compatibility-basis", choices=sorted(VALID_COMPATIBILITY_BASES)
    )
    parser.add_argument(
        "--allow-limited-tro",
        action="store_true",
        help=(
            "Allow a TRO that omits the data_release_manifest artifact. Do not "
            "use this for current US/UK release-manifest-backed bundles."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    validator = BundleValidator()
    manifest = get_release_manifest(args.country)

    validator.validate_manifest(
        manifest,
        expected_model_version=args.expected_model_version,
        expected_data_version=args.expected_data_version,
        expected_built_with_model_version=args.expected_built_with_model_version,
        expected_compatibility_basis=args.expected_compatibility_basis,
    )
    validator.validate_model_wrapper(args.country, manifest)
    validator.validate_tro(
        args.country,
        manifest,
        allow_limited_tro=args.allow_limited_tro,
    )

    if validator.failures:
        print(f"{args.country}: release bundle validation failed", file=sys.stderr)
        for failure in validator.failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(
        f"{args.country}: release bundle valid "
        f"({manifest.model_package.name} {manifest.model_package.version}, "
        f"{manifest.data_package.name} {manifest.data_package.version})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
