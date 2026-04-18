"""TRACE Transparent Research Object (TRO) export.

Emits TROv v0.1 JSON-LD for a PolicyEngine certified runtime bundle. The
TRO is the standards-based provenance surface on top of the internal
release manifests; it pins the model wheel, bundle manifest, data release
manifest, and certified dataset artifact together by sha256 and exposes
certification metadata in machine-readable fields so downstream tooling
does not have to parse prose.

See https://w3id.org/trace/trov/0.1 for the vocabulary and
docs/release-bundles.md for how the bundle layer is composed.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable, Mapping
from typing import Any, Optional

from .release_manifest import (
    CountryReleaseManifest,
    DataCertification,
    DataReleaseManifest,
    fetch_pypi_wheel_metadata,
    https_dataset_uri,
    https_release_manifest_uri,
)

TRACE_TROV_VERSION = "0.1"
POLICYENGINE_TRACE_NAMESPACE = "https://policyengine.org/trace/0.1#"

TRACE_CONTEXT: list[dict[str, str]] = [
    {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "trov": "https://w3id.org/trace/trov/0.1#",
        "schema": "https://schema.org/",
        "pe": POLICYENGINE_TRACE_NAMESPACE,
    }
]

POLICYENGINE_ORGANIZATION: dict[str, str] = {
    "@type": "schema:Organization",
    "schema:name": "PolicyEngine",
    "schema:url": "https://policyengine.org",
}

_MIME_TYPES = {
    "h5": "application/x-hdf5",
    "json": "application/json",
    "jsonld": "application/ld+json",
    "whl": "application/zip",
    "tar.gz": "application/gzip",
}


def _hash_object(value: str) -> dict[str, str]:
    return {
        "trov:hashAlgorithm": "sha256",
        "trov:hashValue": value,
    }


def _artifact_mime_type(path_or_uri: str) -> Optional[str]:
    lowered = path_or_uri.lower()
    if lowered.endswith(".tar.gz"):
        return _MIME_TYPES["tar.gz"]
    suffix = lowered.rsplit(".", 1)[-1] if "." in lowered else ""
    return _MIME_TYPES.get(suffix)


def _canonical_json_bytes(value: Mapping) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compute_trace_composition_fingerprint(
    artifact_hashes: Iterable[str],
) -> str:
    """Fingerprint a composition by the sorted set of its artifact hashes."""
    digest = hashlib.sha256()
    digest.update("".join(sorted(artifact_hashes)).encode("utf-8"))
    return digest.hexdigest()


def _ci_attestation() -> dict[str, str]:
    """Return GitHub Actions attestation metadata if available."""
    attestation: dict[str, str] = {}
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return attestation
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        attestation["pe:ciRunUrl"] = f"{server}/{repo}/actions/runs/{run_id}"
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        attestation["pe:ciGitSha"] = sha
    ref = os.environ.get("GITHUB_REF")
    if ref:
        attestation["pe:ciGitRef"] = ref
    return attestation


def _resolve_model_wheel_hash(
    country_manifest: CountryReleaseManifest,
    *,
    model_wheel_sha256: Optional[str],
    model_wheel_url: Optional[str],
    fetch_pypi: Any,
) -> tuple[Optional[str], Optional[str]]:
    """Return (sha256, https_url) for the model wheel, fetching from PyPI if missing."""
    sha = model_wheel_sha256 or country_manifest.model_package.sha256
    url = model_wheel_url or country_manifest.model_package.wheel_url
    if sha is not None and url is not None:
        return sha, url
    try:
        metadata = fetch_pypi(
            country_manifest.model_package.name,
            country_manifest.model_package.version,
        )
    except Exception:
        return sha, url
    return sha or metadata.get("sha256"), url or metadata.get("url")


def build_trace_tro_from_release_bundle(
    country_manifest: CountryReleaseManifest,
    data_release_manifest: DataReleaseManifest,
    *,
    certification: Optional[DataCertification] = None,
    bundle_manifest_path: Optional[str] = None,
    data_release_manifest_path: Optional[str] = None,
    model_wheel_sha256: Optional[str] = None,
    model_wheel_url: Optional[str] = None,
    fetch_pypi: Any = fetch_pypi_wheel_metadata,
    ci_attestation: Optional[Mapping[str, str]] = None,
) -> dict:
    """Build a TRACE TRO for a certified runtime bundle.

    Artifacts in the composition: bundle manifest, data release manifest,
    certified dataset, and the country model wheel. The wheel hash is read
    from the bundled manifest when available and fetched from PyPI otherwise.

    Certification metadata is encoded as structured ``pe:*`` fields on the
    :class:`trov:TrustedResearchPerformance` node so downstream tools can
    read it without parsing the description.
    """
    certified_artifact = country_manifest.certified_data_artifact
    if certified_artifact is None:
        raise ValueError(
            "Country release manifest does not define a certified artifact."
        )

    dataset_artifact = data_release_manifest.artifacts.get(certified_artifact.dataset)
    if dataset_artifact is None:
        raise ValueError(
            "Data release manifest does not include the certified dataset "
            f"'{certified_artifact.dataset}'."
        )
    if dataset_artifact.sha256 is None:
        raise ValueError(
            "Data release manifest does not include a SHA256 for the certified dataset "
            f"'{certified_artifact.dataset}'."
        )

    effective_certification = certification or country_manifest.certification
    bundle_manifest_location = (
        bundle_manifest_path
        or f"data/release_manifests/{country_manifest.country_id}.json"
    )
    data_manifest_location = data_release_manifest_path or https_release_manifest_uri(
        country_manifest.data_package
    )
    dataset_location = https_dataset_uri(
        repo_id=dataset_artifact.repo_id,
        path_in_repo=dataset_artifact.path,
        revision=dataset_artifact.revision,
    )

    bundle_manifest_payload = country_manifest.model_dump(mode="json")
    data_release_payload = data_release_manifest.model_dump(mode="json")
    bundle_manifest_hash = hashlib.sha256(
        _canonical_json_bytes(bundle_manifest_payload)
    ).hexdigest()
    data_release_manifest_hash = hashlib.sha256(
        _canonical_json_bytes(data_release_payload)
    ).hexdigest()

    model_wheel_sha, model_wheel_https = _resolve_model_wheel_hash(
        country_manifest,
        model_wheel_sha256=model_wheel_sha256,
        model_wheel_url=model_wheel_url,
        fetch_pypi=fetch_pypi,
    )

    artifact_specs: list[dict[str, Any]] = [
        {
            "id": "bundle_manifest",
            "hash": bundle_manifest_hash,
            "location": bundle_manifest_location,
            "mime_type": "application/json",
            "name": f"policyengine.py bundle manifest for {country_manifest.country_id}",
        },
        {
            "id": "data_release_manifest",
            "hash": data_release_manifest_hash,
            "location": data_manifest_location,
            "mime_type": "application/json",
            "name": f"{country_manifest.data_package.name} release manifest "
            f"{country_manifest.data_package.version}",
        },
        {
            "id": "dataset",
            "hash": dataset_artifact.sha256,
            "location": dataset_location,
            "mime_type": _artifact_mime_type(dataset_artifact.path),
            "name": certified_artifact.dataset,
        },
    ]

    if model_wheel_sha is not None:
        artifact_specs.append(
            {
                "id": "model_wheel",
                "hash": model_wheel_sha,
                "location": model_wheel_https
                or f"https://pypi.org/project/{country_manifest.model_package.name}/"
                f"{country_manifest.model_package.version}/",
                "mime_type": _artifact_mime_type(model_wheel_https or "")
                or "application/zip",
                "name": f"{country_manifest.model_package.name}=="
                f"{country_manifest.model_package.version} wheel",
            }
        )

    composition_artifacts: list[dict[str, Any]] = []
    arrangement_locations: list[dict[str, Any]] = []
    artifact_hashes: list[str] = []

    for index, artifact in enumerate(artifact_specs):
        artifact_id = f"composition/1/artifact/{artifact['id']}"
        artifact_hashes.append(artifact["hash"])
        artifact_entry: dict[str, Any] = {
            "@id": artifact_id,
            "@type": "trov:ResearchArtifact",
            "schema:name": artifact["name"],
            "trov:hash": _hash_object(artifact["hash"]),
        }
        if artifact["mime_type"] is not None:
            artifact_entry["trov:mimeType"] = artifact["mime_type"]
        composition_artifacts.append(artifact_entry)
        arrangement_locations.append(
            {
                "@id": f"arrangement/0/location/{artifact['id']}",
                "@type": "trov:ArtifactLocation",
                "trov:artifact": {"@id": artifact_id},
                "trov:path": artifact["location"],
            }
        )

    certification_fields: dict[str, Any] = {}
    certification_description_parts: list[str] = []
    if effective_certification is not None:
        certification_fields["pe:certifiedForModelVersion"] = (
            effective_certification.certified_for_model_version
        )
        certification_fields["pe:compatibilityBasis"] = (
            effective_certification.compatibility_basis
        )
        certification_description_parts.append(
            f"Certified for runtime model version "
            f"{effective_certification.certified_for_model_version} via "
            f"{effective_certification.compatibility_basis}."
        )
        if effective_certification.built_with_model_version is not None:
            certification_fields["pe:builtWithModelVersion"] = (
                effective_certification.built_with_model_version
            )
            certification_description_parts.append(
                f"Built with {country_manifest.model_package.name} "
                f"{effective_certification.built_with_model_version}."
            )
        if effective_certification.built_with_model_git_sha is not None:
            certification_fields["pe:builtWithModelGitSha"] = (
                effective_certification.built_with_model_git_sha
            )
        if effective_certification.data_build_fingerprint is not None:
            certification_fields["pe:dataBuildFingerprint"] = (
                effective_certification.data_build_fingerprint
            )
            certification_description_parts.append(
                f"Data-build fingerprint: "
                f"{effective_certification.data_build_fingerprint}."
            )
        if effective_certification.data_build_id is not None:
            certification_fields["pe:dataBuildId"] = (
                effective_certification.data_build_id
            )
        if effective_certification.certified_by is not None:
            certification_fields["pe:certifiedBy"] = (
                effective_certification.certified_by
            )

    attestation_fields = (
        dict(ci_attestation) if ci_attestation is not None else _ci_attestation()
    )

    created_at = country_manifest.published_at or (
        data_release_manifest.build.built_at
        if data_release_manifest.build is not None
        else None
    )
    started_at = (
        data_release_manifest.build.built_at
        if data_release_manifest.build is not None
        else created_at
    )
    build_id = (
        (
            effective_certification.data_build_id
            if effective_certification is not None
            else None
        )
        or certified_artifact.build_id
        or (
            f"{country_manifest.data_package.name}-{country_manifest.data_package.version}"
        )
    )

    certification_description = (
        " " + " ".join(certification_description_parts)
        if certification_description_parts
        else ""
    )

    tro_node: dict[str, Any] = {
        "@id": "tro",
        "@type": ["trov:TransparentResearchObject", "schema:CreativeWork"],
        "trov:vocabularyVersion": TRACE_TROV_VERSION,
        "schema:creator": POLICYENGINE_ORGANIZATION,
        "schema:name": (
            f"policyengine {country_manifest.country_id} certified bundle TRO"
        ),
        "schema:description": (
            f"TRACE TRO for certified runtime bundle "
            f"{country_manifest.bundle_id or country_manifest.country_id} "
            f"covering the bundled country release manifest, the country data "
            f"release manifest, the certified dataset artifact, and the model "
            f"wheel." + certification_description
        ),
        "trov:wasAssembledBy": {
            "@id": "trs",
            "@type": ["trov:TrustedResearchSystem", "schema:Organization"],
            "schema:name": "PolicyEngine certified release bundle pipeline",
            "schema:description": (
                "PolicyEngine certification workflow for runtime bundles that "
                "pin a country model version, a country data release, and a "
                "specific dataset artifact."
            ),
        },
        "trov:createdWith": {
            "@type": "schema:SoftwareApplication",
            "schema:name": "policyengine",
            "schema:softwareVersion": country_manifest.policyengine_version,
        },
        "trov:hasComposition": {
            "@id": "composition/1",
            "@type": "trov:ArtifactComposition",
            "trov:hasFingerprint": {
                "@id": "fingerprint",
                "@type": "trov:CompositionFingerprint",
                "trov:hash": _hash_object(
                    compute_trace_composition_fingerprint(artifact_hashes)
                ),
            },
            "trov:hasArtifact": composition_artifacts,
        },
        "trov:hasArrangement": [
            {
                "@id": "arrangement/0",
                "@type": "trov:ArtifactArrangement",
                "rdfs:comment": (
                    f"Certified arrangement for bundle "
                    f"{country_manifest.bundle_id or country_manifest.country_id}."
                ),
                "trov:hasArtifactLocation": arrangement_locations,
            }
        ],
        "trov:hasPerformance": [
            {
                "@id": "trp/0",
                "@type": "trov:TrustedResearchPerformance",
                "rdfs:comment": (
                    f"Certification of build {build_id} for "
                    f"{country_manifest.model_package.name} "
                    f"{country_manifest.model_package.version}."
                ),
                "trov:wasConductedBy": {"@id": "trs"},
                "trov:startedAtTime": started_at,
                "trov:endedAtTime": created_at,
                "trov:contributedToArrangement": {
                    "@id": "trp/0/binding/0",
                    "@type": "trov:ArrangementBinding",
                    "trov:arrangement": {"@id": "arrangement/0"},
                },
                **certification_fields,
                **attestation_fields,
            }
        ],
    }
    if created_at is not None:
        tro_node["schema:dateCreated"] = created_at

    return {"@context": TRACE_CONTEXT, "@graph": [tro_node]}


def serialize_trace_tro(tro: Mapping) -> bytes:
    """Serialize a TRO to canonical JSON bytes (sorted keys, trailing newline)."""
    return (json.dumps(tro, indent=2, sort_keys=True) + "\n").encode("utf-8")


def extract_bundle_tro_reference(tro: Mapping) -> dict[str, Any]:
    """Extract a compact reference to a bundle TRO for inclusion in other TROs.

    Returns a dict with the composition fingerprint and the bundle TRO's
    name, suitable for use as an input reference in a per-simulation TRO.
    """
    graph = tro.get("@graph") or []
    if not graph:
        raise ValueError("TRO has an empty graph.")
    node = graph[0]
    fingerprint = (
        node.get("trov:hasComposition", {})
        .get("trov:hasFingerprint", {})
        .get("trov:hash", {})
        .get("trov:hashValue")
    )
    if fingerprint is None:
        raise ValueError("TRO is missing a composition fingerprint.")
    return {
        "fingerprint": fingerprint,
        "name": node.get("schema:name"),
        "policyengine_version": (
            node.get("trov:createdWith", {}).get("schema:softwareVersion")
        ),
    }


def build_simulation_trace_tro(
    *,
    bundle_tro: Mapping,
    results_payload: Mapping,
    reform_payload: Optional[Mapping] = None,
    reform_name: Optional[str] = None,
    simulation_id: Optional[str] = None,
    created_at: Optional[str] = None,
    started_at: Optional[str] = None,
    results_location: Optional[str] = None,
    reform_location: Optional[str] = None,
    bundle_tro_location: Optional[str] = None,
    ci_attestation: Optional[Mapping[str, str]] = None,
) -> dict:
    """Build a per-simulation TRO chaining a bundle TRO to a results payload.

    The simulation TRO's composition includes: the bundle TRO itself (as a
    single hashed artifact), the reform JSON (if provided), and the
    results.json payload. This is the TRO academics cite alongside a
    published result.
    """
    bundle_reference = extract_bundle_tro_reference(bundle_tro)
    bundle_bytes = _canonical_json_bytes(bundle_tro)
    bundle_hash = hashlib.sha256(bundle_bytes).hexdigest()
    results_bytes = _canonical_json_bytes(results_payload)
    results_hash = hashlib.sha256(results_bytes).hexdigest()

    artifact_specs: list[dict[str, Any]] = [
        {
            "id": "bundle_tro",
            "hash": bundle_hash,
            "location": bundle_tro_location
            or f"bundle.trace.tro.jsonld#{bundle_reference['fingerprint']}",
            "mime_type": "application/ld+json",
            "name": bundle_reference.get("name") or "policyengine bundle TRO",
        }
    ]
    if reform_payload is not None:
        reform_bytes = _canonical_json_bytes(reform_payload)
        reform_hash = hashlib.sha256(reform_bytes).hexdigest()
        artifact_specs.append(
            {
                "id": "reform",
                "hash": reform_hash,
                "location": reform_location or "reform.json",
                "mime_type": "application/json",
                "name": reform_name or "reform",
            }
        )
    artifact_specs.append(
        {
            "id": "results",
            "hash": results_hash,
            "location": results_location or "results.json",
            "mime_type": "application/json",
            "name": "results.json",
        }
    )

    composition_artifacts: list[dict[str, Any]] = []
    arrangement_locations: list[dict[str, Any]] = []
    artifact_hashes: list[str] = []
    for artifact in artifact_specs:
        artifact_id = f"composition/1/artifact/{artifact['id']}"
        artifact_hashes.append(artifact["hash"])
        composition_artifacts.append(
            {
                "@id": artifact_id,
                "@type": "trov:ResearchArtifact",
                "schema:name": artifact["name"],
                "trov:hash": _hash_object(artifact["hash"]),
                "trov:mimeType": artifact["mime_type"],
            }
        )
        arrangement_locations.append(
            {
                "@id": f"arrangement/0/location/{artifact['id']}",
                "@type": "trov:ArtifactLocation",
                "trov:artifact": {"@id": artifact_id},
                "trov:path": artifact["location"],
            }
        )

    attestation_fields = (
        dict(ci_attestation) if ci_attestation is not None else _ci_attestation()
    )
    simulation_slug = simulation_id or "simulation"

    tro_node: dict[str, Any] = {
        "@id": "tro",
        "@type": ["trov:TransparentResearchObject", "schema:CreativeWork"],
        "trov:vocabularyVersion": TRACE_TROV_VERSION,
        "schema:creator": POLICYENGINE_ORGANIZATION,
        "schema:name": f"policyengine simulation TRO ({simulation_slug})",
        "schema:description": (
            "TRACE TRO for a PolicyEngine simulation result. Composition pins "
            "the certified runtime bundle TRO, the reform specification "
            "(where applicable), and the results.json payload."
        ),
        "trov:createdWith": {
            "@type": "schema:SoftwareApplication",
            "schema:name": "policyengine",
            "schema:softwareVersion": bundle_reference.get("policyengine_version"),
        },
        "trov:wasAssembledBy": {
            "@id": "trs",
            "@type": ["trov:TrustedResearchSystem", "schema:Organization"],
            "schema:name": "PolicyEngine simulation pipeline",
            "schema:description": (
                "PolicyEngine simulation that consumes a certified runtime "
                "bundle and produces a results.json payload."
            ),
        },
        "trov:hasComposition": {
            "@id": "composition/1",
            "@type": "trov:ArtifactComposition",
            "trov:hasFingerprint": {
                "@id": "fingerprint",
                "@type": "trov:CompositionFingerprint",
                "trov:hash": _hash_object(
                    compute_trace_composition_fingerprint(artifact_hashes)
                ),
            },
            "trov:hasArtifact": composition_artifacts,
        },
        "trov:hasArrangement": [
            {
                "@id": "arrangement/0",
                "@type": "trov:ArtifactArrangement",
                "rdfs:comment": f"Simulation arrangement for {simulation_slug}.",
                "trov:hasArtifactLocation": arrangement_locations,
            }
        ],
        "trov:hasPerformance": [
            {
                "@id": "trp/0",
                "@type": "trov:TrustedResearchPerformance",
                "rdfs:comment": (
                    f"PolicyEngine simulation bound to bundle fingerprint "
                    f"{bundle_reference['fingerprint']}."
                ),
                "trov:wasConductedBy": {"@id": "trs"},
                "trov:startedAtTime": started_at or created_at,
                "trov:endedAtTime": created_at,
                "trov:contributedToArrangement": {
                    "@id": "trp/0/binding/0",
                    "@type": "trov:ArrangementBinding",
                    "trov:arrangement": {"@id": "arrangement/0"},
                },
                "pe:bundleFingerprint": bundle_reference["fingerprint"],
                **attestation_fields,
            }
        ],
    }
    if created_at is not None:
        tro_node["schema:dateCreated"] = created_at

    return {"@context": TRACE_CONTEXT, "@graph": [tro_node]}
