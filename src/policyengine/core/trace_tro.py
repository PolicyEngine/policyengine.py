from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping

from .release_manifest import (
    CountryReleaseManifest,
    DataCertification,
    DataReleaseManifest,
)

TRACE_TROV_VERSION = "0.1"
TRACE_CONTEXT = [
    {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "trov": "https://w3id.org/trace/trov/0.1#",
        "schema": "https://schema.org/",
    }
]


def _hash_object(value: str) -> dict[str, str]:
    return {
        "trov:hashAlgorithm": "sha256",
        "trov:hashValue": value,
    }


def _artifact_mime_type(path_or_uri: str) -> str | None:
    suffix = path_or_uri.rsplit(".", 1)[-1].lower() if "." in path_or_uri else ""
    return {
        "h5": "application/x-hdf5",
        "json": "application/json",
        "jsonld": "application/ld+json",
    }.get(suffix)


def _canonical_json_bytes(value: Mapping) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compute_trace_composition_fingerprint(
    artifact_hashes: Iterable[str],
) -> str:
    digest = hashlib.sha256()
    digest.update("".join(sorted(artifact_hashes)).encode("utf-8"))
    return digest.hexdigest()


def build_trace_tro_from_release_bundle(
    country_manifest: CountryReleaseManifest,
    data_release_manifest: DataReleaseManifest,
    *,
    certification: DataCertification | None = None,
    bundle_manifest_path: str | None = None,
    data_release_manifest_path: str | None = None,
) -> dict:
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
    data_manifest_location = data_release_manifest_path or (
        "https://huggingface.co/"
        f"{country_manifest.data_package.repo_id}/resolve/"
        f"{country_manifest.data_package.version}/"
        f"{country_manifest.data_package.release_manifest_path}"
    )

    bundle_manifest_payload = country_manifest.model_dump(mode="json")
    data_release_payload = data_release_manifest.model_dump(mode="json")
    bundle_manifest_hash = hashlib.sha256(
        _canonical_json_bytes(bundle_manifest_payload)
    ).hexdigest()
    data_release_manifest_hash = hashlib.sha256(
        _canonical_json_bytes(data_release_payload)
    ).hexdigest()

    artifact_specs = [
        {
            "hash": bundle_manifest_hash,
            "location": bundle_manifest_location,
            "mime_type": "application/json",
        },
        {
            "hash": data_release_manifest_hash,
            "location": data_manifest_location,
            "mime_type": "application/json",
        },
        {
            "hash": dataset_artifact.sha256,
            "location": certified_artifact.uri,
            "mime_type": _artifact_mime_type(certified_artifact.uri),
        },
    ]

    composition_artifacts = []
    arrangement_locations = []
    artifact_hashes = []

    for index, artifact in enumerate(artifact_specs):
        artifact_id = f"composition/1/artifact/{index}"
        artifact_hashes.append(artifact["hash"])
        artifact_entry = {
            "@id": artifact_id,
            "@type": "trov:ResearchArtifact",
            "trov:hash": _hash_object(artifact["hash"]),
        }
        if artifact["mime_type"] is not None:
            artifact_entry["trov:mimeType"] = artifact["mime_type"]
        composition_artifacts.append(artifact_entry)
        arrangement_locations.append(
            {
                "@id": f"arrangement/0/location/{index}",
                "@type": "trov:ArtifactLocation",
                "trov:artifact": {"@id": artifact_id},
                "trov:path": artifact["location"],
            }
        )

    certification_description = ""
    if effective_certification is not None:
        certification_description = (
            f" Certified for runtime model version "
            f"{effective_certification.certified_for_model_version} via "
            f"{effective_certification.compatibility_basis}."
        )
        if effective_certification.built_with_model_version is not None:
            certification_description += (
                f" Built with {country_manifest.model_package.name} "
                f"{effective_certification.built_with_model_version}."
            )
        if effective_certification.data_build_fingerprint is not None:
            certification_description += (
                f" Data-build fingerprint: "
                f"{effective_certification.data_build_fingerprint}."
            )

    created_at = country_manifest.published_at or (
        data_release_manifest.build.built_at
        if data_release_manifest.build is not None
        else None
    )
    build_id = (
        effective_certification.data_build_id
        if effective_certification is not None
        else (
            certified_artifact.build_id
            or f"{country_manifest.data_package.name}-{country_manifest.data_package.version}"
        )
    )

    return {
        "@context": TRACE_CONTEXT,
        "@graph": [
            {
                "@id": "tro",
                "@type": ["trov:TransparentResearchObject", "schema:CreativeWork"],
                "trov:vocabularyVersion": TRACE_TROV_VERSION,
                "schema:creator": country_manifest.policyengine_version,
                "schema:name": (
                    f"policyengine {country_manifest.country_id} certified bundle TRO"
                ),
                "schema:description": (
                    f"TRACE TRO for certified runtime bundle "
                    f"{country_manifest.bundle_id or country_manifest.country_id} "
                    f"covering the bundled country release manifest, the country data "
                    f"release manifest, and the certified dataset artifact."
                    f"{certification_description}"
                ),
                "schema:dateCreated": created_at,
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
                        "trov:startedAtTime": (
                            data_release_manifest.build.built_at
                            if data_release_manifest.build is not None
                            else created_at
                        ),
                        "trov:endedAtTime": created_at,
                        "trov:contributedToArrangement": {
                            "@id": "trp/0/binding/0",
                            "@type": "trov:ArrangementBinding",
                            "trov:arrangement": {"@id": "arrangement/0"},
                        },
                    }
                ],
            }
        ],
    }


def serialize_trace_tro(tro: Mapping) -> bytes:
    return (json.dumps(tro, indent=2, sort_keys=True) + "\n").encode("utf-8")
