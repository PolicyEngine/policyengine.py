"""Versioned execution identities and receipts.

The models in this module describe what a caller requested separately from
what actually executed.  They are intentionally engine-neutral: a runtime can
be PolicyEngine Core, Axiom, or another engine, while ruleset and population
artifacts remain optional.

Receipts snapshot release-manifest fields into strict schema-v1 DTOs and use
compact TRACE references. They do not replace
:attr:`policyengine.core.Simulation.release_bundle` or the full TRACE TRO
emitted by a simulation run record.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Literal, Mapping, Optional, Union

import rfc8785
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from policyengine.provenance.manifest import CountryReleaseManifest
from policyengine.provenance.trace import (
    canonical_json_bytes,
    extract_bundle_tro_reference,
)

EXECUTION_RECEIPT_SCHEMA_VERSION: Literal[1] = 1
EXECUTION_RECEIPT_CANONICALIZATION = "RFC8785-JCS"
SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ExecutionContractModel(BaseModel):
    """Strict base model for the public execution contract."""

    model_config = ConfigDict(extra="forbid")


class PackageVersion(ExecutionContractModel):
    """Strict package identity frozen by execution-receipt schema v1."""

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    wheel_url: Optional[str] = None


class DataPackageVersion(PackageVersion):
    """Strict data-package identity in a certified release snapshot."""

    repo_id: str = Field(min_length=1)
    repo_type: str = Field(min_length=1)
    release_manifest_path: str = Field(min_length=1)
    release_manifest_revision: Optional[str] = None


class ArtifactPathReference(ExecutionContractModel):
    """Strict dataset artifact reference in a certified release snapshot."""

    path: str = Field(min_length=1)
    revision: Optional[str] = None
    sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    metadata_sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    repo_id: Optional[str] = None
    repo_type: Optional[str] = None


class ArtifactPathTemplate(ExecutionContractModel):
    """Strict region-dataset path template."""

    path_template: str = Field(min_length=1)


class CertifiedDataArtifact(ExecutionContractModel):
    """Certified population artifact attached to a release snapshot."""

    data_package: Optional[PackageVersion] = None
    dataset: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    build_id: Optional[str] = None


class DataCertification(ExecutionContractModel):
    """Strict certification statement for a release's population data."""

    compatibility_basis: str = Field(min_length=1)
    certified_for_model_version: str = Field(min_length=1)
    data_build_id: Optional[str] = None
    built_with_model_version: Optional[str] = None
    built_with_model_git_sha: Optional[str] = None
    data_build_fingerprint: Optional[str] = None
    certified_by: Optional[str] = None


class CertifiedReleaseManifest(ExecutionContractModel):
    """Strict, serialized snapshot of a certified country release.

    This receipt-owned DTO deliberately excludes the source model's private
    ``source_sha256`` field. Freezing the nested shape prevents unknown future
    manifest fields from being silently discarded by receipt v1 readers.
    """

    schema_version: int
    bundle_id: Optional[str] = None
    published_at: Optional[str] = None
    country_id: str = Field(min_length=1)
    policyengine_version: str = Field(min_length=1)
    model_package: PackageVersion
    data_package: DataPackageVersion
    default_dataset: str = Field(min_length=1)
    datasets: dict[str, ArtifactPathReference]
    region_datasets: dict[str, ArtifactPathTemplate]
    certified_data_artifact: Optional[CertifiedDataArtifact] = None
    certification: Optional[DataCertification] = None

    @classmethod
    def from_country_release_manifest(
        cls, manifest: CountryReleaseManifest
    ) -> CertifiedReleaseManifest:
        """Copy the public serialized fields from an existing manifest."""

        return cls.model_validate(manifest.model_dump(mode="json"))


class RequestedExecutionAliases(ExecutionContractModel):
    """Caller-supplied selectors, which may be mutable aliases.

    Values such as ``latest`` and ``default`` belong here.  The
    :class:`ResolvedExecutionBundle` records the concrete identities selected
    for the run.
    """

    engine: Optional[str] = None
    bundle: Optional[str] = None
    model: Optional[str] = None
    data: Optional[str] = None
    ruleset: Optional[str] = None
    population: Optional[str] = None
    numeric_mode: Optional[str] = None


class ArtifactIdentity(ExecutionContractModel):
    """Resolved identity for a runtime, ruleset, or population artifact."""

    name: str = Field(min_length=1)
    version: Optional[str] = None
    uri: Optional[str] = None
    revision: Optional[str] = None
    sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    build_id: Optional[str] = None

    @model_validator(mode="after")
    def _require_resolved_identity(self) -> ArtifactIdentity:
        if not any((self.version, self.uri, self.revision, self.sha256, self.build_id)):
            raise ValueError(
                "A resolved artifact needs a version, URI, revision, sha256, "
                "or build_id."
            )
        return self


class RuntimeIdentity(ExecutionContractModel):
    """Concrete identity of the engine that performed the calculation."""

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    git_sha: Optional[str] = None
    artifact: Optional[ArtifactIdentity] = None


class PackageResolution(ExecutionContractModel):
    """Actual and certified identities for one package role.

    ``actual`` is the package used by the process. ``certified`` is the
    package selected by release metadata.  Keeping both prevents an installed
    version mismatch from being reported as though the certified package ran.
    A resolution without ``actual`` is invalid: certification context alone
    belongs in :class:`CertifiedReleaseManifest`, not in a field describing a
    component that executed.
    """

    actual: PackageVersion
    certified: Optional[PackageVersion] = None

    @classmethod
    def from_release_bundle(
        cls,
        release_bundle: Mapping[str, Any],
        component: Literal["model", "data"],
        *,
        actual: PackageVersion,
    ) -> PackageResolution:
        """Resolve one used package role from the existing dict API.

        The release bundle supplies only the certified selection. Callers must
        pass ``actual`` explicitly when the component was loaded; this method
        never assumes the certified package is what ran. Invoke this only for
        components the execution actually used.
        """

        if component not in ("model", "data"):
            raise ValueError("component must be 'model' or 'data'")
        name = release_bundle.get(f"{component}_package")
        version = release_bundle.get(f"{component}_version")
        if (name is None) != (version is None):
            raise ValueError(
                f"release_bundle has an incomplete certified {component} package"
            )
        certified = (
            PackageVersion(name=str(name), version=str(version))
            if name is not None
            else None
        )
        return cls(actual=actual, certified=certified)


class TraceReference(ExecutionContractModel):
    """Compact reference to an existing TRACE Transparent Research Object."""

    composition_fingerprint: str = Field(pattern=SHA256_PATTERN)
    sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    url: Optional[str] = None
    name: Optional[str] = None

    @classmethod
    def from_trace_tro(
        cls,
        tro: Mapping[str, Any],
        *,
        url: Optional[str] = None,
    ) -> TraceReference:
        """Build a compact reference with the existing TRACE extractor."""

        reference = extract_bundle_tro_reference(tro)
        return cls(
            composition_fingerprint=reference["fingerprint"],
            # TRACE serializes TROs with its established pretty canonical form;
            # this digest identifies those exact published bytes rather than
            # the semantic RFC 8785 request/result hash used by receipts.
            sha256=hashlib.sha256(canonical_json_bytes(tro)).hexdigest(),
            url=url or reference.get("self_url"),
            name=reference.get("name"),
        )


class ResolvedExecutionBundle(ExecutionContractModel):
    """Concrete runtime and artifacts used for an execution.

    ``model`` and ``data`` are absent when that package role was not part of
    the run.  In particular, a household calculation that did not load
    population data should leave both ``data`` and ``population_artifact``
    unset, even when its selected release also certifies population data.

    ``certified_release`` freezes the public fields of a
    :class:`CountryReleaseManifest` as release context. Its presence does not
    by itself claim that every component in that release was accessed; used
    components are the explicit fields above.
    """

    runtime: RuntimeIdentity
    numeric_mode: str = Field(min_length=1)
    model: Optional[PackageResolution] = None
    data: Optional[PackageResolution] = None
    ruleset_artifact: Optional[ArtifactIdentity] = None
    population_artifact: Optional[ArtifactIdentity] = None
    certified_release: Optional[CertifiedReleaseManifest] = None
    bundle_trace: Optional[TraceReference] = None

    @field_validator("certified_release", mode="before")
    @classmethod
    def _copy_certified_release(cls, value: Any) -> Optional[CertifiedReleaseManifest]:
        if value is None or isinstance(value, CertifiedReleaseManifest):
            return value
        if isinstance(value, CountryReleaseManifest):
            return CertifiedReleaseManifest.from_country_release_manifest(value)
        return CertifiedReleaseManifest.model_validate(value)

    @model_validator(mode="after")
    def _certified_packages_match_release(self) -> ResolvedExecutionBundle:
        if self.certified_release is None:
            return self
        expected = {
            "model": self.certified_release.model_package,
            "data": self.certified_release.data_package,
        }
        for component, resolution in (("model", self.model), ("data", self.data)):
            if resolution is None or resolution.certified is None:
                continue
            package = resolution.certified
            release_package = expected[component]
            claimed_fields = package.model_dump(mode="json", exclude_none=True)
            release_fields = release_package.model_dump(mode="json")
            for field, claimed_value in claimed_fields.items():
                if claimed_value != release_fields.get(field):
                    raise ValueError(
                        f"Certified {component} package field {field!r} does not "
                        "match certified_release."
                    )
        return self


class ExecutionReceipt(ExecutionContractModel):
    """Versioned, JSON-serializable receipt for one execution."""

    schema_version: Literal[1] = EXECUTION_RECEIPT_SCHEMA_VERSION
    requested: RequestedExecutionAliases = Field(
        default_factory=RequestedExecutionAliases
    )
    resolved: ResolvedExecutionBundle
    run_id: Optional[str] = None
    created_at: Optional[datetime] = None
    request_sha256: Optional[str] = Field(
        default=None,
        pattern=SHA256_PATTERN,
        description="SHA-256 of RFC 8785 JCS canonical request bytes.",
    )
    result_sha256: Optional[str] = Field(
        default=None,
        pattern=SHA256_PATTERN,
        description="SHA-256 of RFC 8785 JCS canonical result bytes.",
    )

    def content_hash(self) -> str:
        """Return the receipt's canonical SHA-256 content hash."""

        return canonical_content_hash(self)


def canonical_content_hash(value: Union[BaseModel, Mapping[str, Any]]) -> str:
    """Hash semantic JSON content with RFC 8785 JCS canonicalization.

    Receipt schema v1 fixes ``RFC8785-JCS`` as its cross-language byte format.
    The returned lowercase, 64-character digest is therefore portable across
    Python, Rust, and TypeScript implementations. RFC 8785 rejects non-finite
    numbers and non-string object keys rather than producing non-standard JSON.

    This differs intentionally from TRACE's established pretty canonical
    serialization, which identifies exact TRO document bytes.
    """

    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


__all__ = [
    "EXECUTION_RECEIPT_CANONICALIZATION",
    "EXECUTION_RECEIPT_SCHEMA_VERSION",
    "ArtifactIdentity",
    "ArtifactPathReference",
    "ArtifactPathTemplate",
    "CertifiedDataArtifact",
    "CertifiedReleaseManifest",
    "DataCertification",
    "DataPackageVersion",
    "ExecutionReceipt",
    "PackageResolution",
    "PackageVersion",
    "RequestedExecutionAliases",
    "ResolvedExecutionBundle",
    "RuntimeIdentity",
    "TraceReference",
    "canonical_content_hash",
]
