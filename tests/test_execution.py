"""Public execution-contract and receipt tests."""

import hashlib
import json
import math

import pytest
import rfc8785
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from policyengine.execution import (
    ArtifactIdentity,
    CertifiedReleaseManifest,
    ExecutionReceipt,
    PackageResolution,
    PackageVersion,
    ResolvedExecutionBundle,
    RuntimeIdentity,
    TraceReference,
    canonical_content_hash,
)
from policyengine.provenance.manifest import get_release_manifest
from policyengine.provenance.trace import canonical_json_bytes

from .fixtures.execution_fixtures import make_execution_receipt


class TestExecutionReceipt:
    def test__given_aliases_and_resolved_versions__then_both_survive_json_round_trip(
        self,
    ):
        # Given
        receipt = make_execution_receipt()

        # When
        payload = json.loads(receipt.model_dump_json())
        restored = ExecutionReceipt.model_validate(payload)

        # Then
        assert payload["requested"]["model"] == "latest"
        assert payload["resolved"]["model"]["actual"]["version"] == "1.765.0"
        assert (
            payload["resolved"]["model"]["certified"]["version"]
            == get_release_manifest("us").model_package.version
        )
        assert restored.model_dump(mode="json") == payload

    def test__given_receipt__then_generated_json_schema_validates_payload(self):
        # Given
        receipt = make_execution_receipt()
        schema = ExecutionReceipt.model_json_schema()

        # When
        Draft202012Validator.check_schema(schema)
        errors = list(
            Draft202012Validator(schema).iter_errors(receipt.model_dump(mode="json"))
        )

        # Then
        assert errors == []
        assert schema["properties"]["schema_version"]["const"] == 1
        release_properties = schema["$defs"]["CertifiedReleaseManifest"]["properties"]
        assert "source_sha256" not in release_properties

    def test__given_unknown_nested_release_field__then_validation_fails(self):
        # Given
        payload = make_execution_receipt().model_dump(mode="json")
        payload["resolved"]["certified_release"]["model_package"]["unknown"] = (
            "silently-lost"
        )

        # When / Then
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ExecutionReceipt.model_validate(payload)

    def test__given_country_manifest__then_receipt_snapshot_round_trips_strictly(self):
        # Given
        release = get_release_manifest("us")

        # When
        snapshot = CertifiedReleaseManifest.from_country_release_manifest(release)
        restored = CertifiedReleaseManifest.model_validate(
            snapshot.model_dump(mode="json")
        )

        # Then
        assert restored == snapshot
        assert "source_sha256" not in snapshot.model_dump(mode="json")

    def test__given_household_without_population_data__then_data_identity_is_absent(
        self,
    ):
        # Given
        release = get_release_manifest("us")

        # When
        resolved = ResolvedExecutionBundle(
            runtime=RuntimeIdentity(name="axiom", version="0.4.0"),
            numeric_mode="exact-decimal",
            ruleset_artifact=ArtifactIdentity(
                name="us-federal-2026",
                revision="rulespec-deadbeef",
                sha256="a" * 64,
            ),
            certified_release=release,
        )

        # Then
        assert resolved.data is None
        assert resolved.population_artifact is None

    def test__given_certified_package_mismatch__then_validation_fails(self):
        # Given
        release = get_release_manifest("us")

        # When / Then
        with pytest.raises(ValidationError, match="does not match"):
            ResolvedExecutionBundle(
                runtime=RuntimeIdentity(name="policyengine-core", version="3.30.0"),
                numeric_mode="numpy-native",
                model=PackageResolution(
                    actual=PackageVersion(
                        name="policyengine-us",
                        version="1.765.0",
                    ),
                    certified=PackageVersion(
                        name="policyengine-us",
                        version="0.0.1",
                    ),
                ),
                certified_release=release,
            )

    @pytest.mark.parametrize(
        ("field", "mismatched_value"),
        [
            ("sha256", "f" * 64),
            ("wheel_url", "https://example.test/wrong-package.whl"),
        ],
    )
    def test__given_certified_package_metadata_mismatch__then_validation_fails(
        self,
        field,
        mismatched_value,
    ):
        # Given
        release = get_release_manifest("us")
        certified = PackageVersion.model_validate(
            release.model_package.model_dump(mode="json")
        ).model_copy(update={field: mismatched_value})

        # When / Then
        with pytest.raises(ValidationError, match=field):
            ResolvedExecutionBundle(
                runtime=RuntimeIdentity(name="policyengine-core", version="3.30.0"),
                numeric_mode="numpy-native",
                model=PackageResolution(
                    actual=PackageVersion(
                        name="policyengine-us",
                        version="1.765.0",
                    ),
                    certified=certified,
                ),
                certified_release=release,
            )

    def test__given_wrong_schema_version__then_validation_fails(self):
        # Given
        payload = make_execution_receipt().model_dump(mode="json")
        payload["schema_version"] = 2

        # When / Then
        with pytest.raises(ValidationError):
            ExecutionReceipt.model_validate(payload)

    def test__given_no_resolved_numeric_mode__then_validation_fails(self):
        # Given
        payload = {
            "runtime": {
                "name": "policyengine-core",
                "version": "3.30.0",
            }
        }

        # When / Then
        with pytest.raises(ValidationError):
            ResolvedExecutionBundle.model_validate(payload)


class TestPackageResolution:
    def test__given_release_bundle__then_certified_and_actual_stay_distinct(self):
        # Given
        release_bundle = {
            "model_package": "policyengine-us",
            "model_version": "1.764.6",
            "data_package": "populace-data",
            "data_version": "0.1.0",
        }
        original = dict(release_bundle)
        actual = PackageVersion(name="policyengine-us", version="1.765.0")

        # When
        resolution = PackageResolution.from_release_bundle(
            release_bundle,
            "model",
            actual=actual,
        )

        # Then
        assert resolution.actual.version == "1.765.0"
        assert resolution.certified.version == "1.764.6"
        assert release_bundle == original

    def test__given_incomplete_release_bundle__then_validation_fails(self):
        # Given
        release_bundle = {"model_package": "policyengine-us"}
        actual = PackageVersion(name="policyengine-us", version="1.765.0")

        # When / Then
        with pytest.raises(ValueError, match="incomplete"):
            PackageResolution.from_release_bundle(
                release_bundle,
                "model",
                actual=actual,
            )

    def test__given_certification_without_actual_package__then_validation_fails(self):
        # Given / When / Then
        with pytest.raises(ValidationError, match="actual"):
            PackageResolution(
                certified=PackageVersion(
                    name="policyengine-us",
                    version="1.764.6",
                )
            )


class TestContentIdentity:
    def test__given_same_mapping_in_different_order__then_hashes_match(self):
        # Given
        first = {"requested": {"model": "latest"}, "period": "2026"}
        second = {"period": "2026", "requested": {"model": "latest"}}

        # When
        first_hash = canonical_content_hash(first)
        second_hash = canonical_content_hash(second)

        # Then
        assert first_hash == second_hash
        assert len(first_hash) == 64

    @pytest.mark.parametrize(
        ("value", "canonical_bytes"),
        [
            ({"small": 1e-6}, b'{"small":0.000001}'),
            ({"large": 1e30}, b'{"large":1e+30}'),
            ({"unicode": "\u20ac\u00e9"}, '{"unicode":"\u20ac\u00e9"}'.encode()),
        ],
    )
    def test__given_cross_language_json_value__then_hash_uses_rfc8785(
        self, value, canonical_bytes
    ):
        # When / Then
        assert (
            canonical_content_hash(value) == hashlib.sha256(canonical_bytes).hexdigest()
        )

    def test__given_non_finite_number__then_hashing_refuses_non_json_value(self):
        # Given / When / Then
        with pytest.raises(rfc8785.FloatDomainError):
            canonical_content_hash({"value": math.nan})

    def test__given_resolved_runtime_changes__then_receipt_hash_changes(self):
        # Given
        receipt = make_execution_receipt()
        changed_resolved = receipt.resolved.model_copy(
            update={
                "runtime": RuntimeIdentity(
                    name="axiom-rules-engine",
                    version="0.4.0",
                )
            }
        )
        changed = receipt.model_copy(update={"resolved": changed_resolved})

        # When
        original_hash = receipt.content_hash()
        changed_hash = changed.content_hash()

        # Then
        assert original_hash != changed_hash

    def test__given_invalid_sha256__then_validation_fails(self):
        # Given / When / Then
        with pytest.raises(ValidationError):
            ArtifactIdentity(name="ruleset", revision="abc", sha256="not-a-hash")

    def test__given_trace_tro__then_reference_uses_trace_fingerprint_and_hash(self):
        # Given
        tro = {
            "@graph": [
                {
                    "@type": "trov:TransparentResearchObject",
                    "schema:name": "test bundle",
                    "pe:selfUrl": "https://example.test/bundle.trace.tro.jsonld",
                    "trov:hasComposition": {
                        "trov:hasFingerprint": {"trov:sha256": "b" * 64}
                    },
                }
            ]
        }

        # When
        reference = TraceReference.from_trace_tro(tro)

        # Then
        assert reference.composition_fingerprint == "b" * 64
        assert reference.sha256 == hashlib.sha256(canonical_json_bytes(tro)).hexdigest()
        assert reference.url == "https://example.test/bundle.trace.tro.jsonld"
