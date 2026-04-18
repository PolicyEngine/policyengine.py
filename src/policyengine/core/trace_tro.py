"""TRACE Transparent Research Object (TRO) export.

Emits JSON-LD that conforms to the TRACE TROv vocabulary
(https://w3id.org/trace/2023/05/trov#) for a PolicyEngine certified
runtime bundle or a PolicyEngine simulation result. The bundle TRO pins
the country model wheel, the country data release manifest, the
certified dataset, and the bundle manifest itself by sha256. The
per-simulation TRO chains a bundle TRO to a reform and a results.json
payload so a published result has an immutable composition fingerprint.

PolicyEngine-specific certification metadata lives under the ``pe:``
namespace and does not pollute the TROv vocabulary, so generated TROs
can still be validated against TROv SHACL shapes when tooling is
available.

See docs/release-bundles.md for how the bundle layer is composed.
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

TRACE_TROV_NAMESPACE = "https://w3id.org/trace/2023/05/trov#"
POLICYENGINE_TRACE_NAMESPACE = "https://policyengine.org/trace/0.1#"

TRACE_CONTEXT: list[dict[str, str]] = [
    {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "trov": TRACE_TROV_NAMESPACE,
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


def _artifact_mime_type(path_or_uri: str) -> Optional[str]:
    lowered = path_or_uri.lower()
    if lowered.endswith(".tar.gz"):
        return _MIME_TYPES["tar.gz"]
    suffix = lowered.rsplit(".", 1)[-1] if "." in lowered else ""
    return _MIME_TYPES.get(suffix)


def canonical_json_bytes(value: Mapping) -> bytes:
    """Canonical JSON serialization used for every content hash in the TRO.

    Documented publicly because any third-party verifier needs to
    reproduce these bytes exactly to recompute the artifact hashes that
    the composition fingerprint binds together.
    """
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compute_trace_composition_fingerprint(
    artifact_hashes: Iterable[str],
) -> str:
    """Fingerprint a composition by the sorted set of its artifact hashes.

    Joins hashes with ``\\n`` so concatenation is unambiguous regardless
    of hash length.
    """
    sorted_hashes = sorted(artifact_hashes)
    digest = hashlib.sha256()
    digest.update("\n".join(sorted_hashes).encode("utf-8"))
    return digest.hexdigest()


def _emission_context() -> dict[str, str]:
    """Attestation metadata about where and how the TRO was emitted.

    Always includes ``pe:emittedIn`` so a verifier can distinguish a CI
    build from a laptop build without inferring from the absence of
    optional fields.
    """
    context: dict[str, str] = {}
    if os.environ.get("GITHUB_ACTIONS") == "true":
        context["pe:emittedIn"] = "github-actions"
        server = os.environ.get("GITHUB_SERVER_URL")
        repo = os.environ.get("GITHUB_REPOSITORY")
        run_id = os.environ.get("GITHUB_RUN_ID")
        if server and repo and run_id:
            context["pe:ciRunUrl"] = f"{server}/{repo}/actions/runs/{run_id}"
        sha = os.environ.get("GITHUB_SHA")
        if sha:
            context["pe:ciGitSha"] = sha
        ref = os.environ.get("GITHUB_REF")
        if ref:
            context["pe:ciGitRef"] = ref
    else:
        context["pe:emittedIn"] = "local"
    return context


def _resolve_model_wheel(
    country_manifest: CountryReleaseManifest,
    *,
    model_wheel_sha256: Optional[str],
    model_wheel_url: Optional[str],
    fetch_pypi: Any,
) -> tuple[Optional[str], Optional[str]]:
    """Return ``(sha256, https_url)`` for the model wheel.

    Uses the bundled manifest when both are present; otherwise queries
    the PyPI JSON API. Network failures degrade to ``(None, None)`` so
    the wheel artifact is omitted rather than breaking emission.
    """
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


def _make_artifact(
    artifact_id: str, sha256: str, mime_type: Optional[str], name: Optional[str]
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "@id": artifact_id,
        "@type": "trov:ResearchArtifact",
        "trov:sha256": sha256,
    }
    if mime_type is not None:
        artifact["trov:mimeType"] = mime_type
    if name is not None:
        artifact["schema:name"] = name
    return artifact


def _make_location(location_id: str, artifact_id: str, location: str) -> dict[str, Any]:
    return {
        "@id": location_id,
        "@type": "trov:ArtifactLocation",
        "trov:hasArtifact": {"@id": artifact_id},
        "trov:hasLocation": location,
    }


_COMPOSITION_ID = "composition/1"
_ARRANGEMENT_ID = "arrangement/1"


def _assemble_composition_and_arrangement(
    artifact_specs: list[dict[str, Any]],
    *,
    arrangement_comment: Optional[str] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    hashes: list[str] = []
    for spec in artifact_specs:
        artifact_id = f"{_COMPOSITION_ID}/artifact/{spec['id']}"
        hashes.append(spec["hash"])
        artifacts.append(
            _make_artifact(
                artifact_id,
                spec["hash"],
                spec.get("mime_type"),
                spec.get("name"),
            )
        )
        locations.append(
            _make_location(
                f"{_ARRANGEMENT_ID}/location/{spec['id']}",
                artifact_id,
                spec["location"],
            )
        )

    composition = {
        "@id": _COMPOSITION_ID,
        "@type": "trov:ArtifactComposition",
        "trov:hasFingerprint": {
            "@id": f"{_COMPOSITION_ID}/fingerprint",
            "@type": "trov:CompositionFingerprint",
            "trov:sha256": compute_trace_composition_fingerprint(hashes),
        },
        "trov:hasArtifact": artifacts,
    }
    arrangement: dict[str, Any] = {
        "@id": _ARRANGEMENT_ID,
        "@type": "trov:ArtifactArrangement",
        "trov:hasArtifactLocation": locations,
    }
    if arrangement_comment is not None:
        arrangement["rdfs:comment"] = arrangement_comment
    return composition, arrangement


def _policyengine_trs(comment: str) -> dict[str, Any]:
    return {
        "@id": "trs",
        "@type": "trov:TransparentResearchSystem",
        "schema:name": "PolicyEngine release pipeline",
        "rdfs:comment": comment,
    }


def _assemble_tro_node(
    *,
    tro_name: str,
    tro_description: str,
    created_at: Optional[str],
    creator: Mapping[str, str],
    software_version: Optional[str],
    trs_comment: str,
    composition: Mapping[str, Any],
    arrangement: Mapping[str, Any],
    performance: Mapping[str, Any],
    self_url: Optional[str] = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "@id": "tro",
        "@type": "trov:TransparentResearchObject",
        "schema:name": tro_name,
        "schema:description": tro_description,
        "schema:creator": dict(creator),
        "trov:wasAssembledBy": _policyengine_trs(trs_comment),
        "trov:createdWith": {
            "@type": "schema:SoftwareApplication",
            "schema:name": "policyengine",
            "schema:softwareVersion": software_version,
        },
        "trov:hasComposition": dict(composition),
        "trov:hasArrangement": [dict(arrangement)],
        "trov:hasPerformance": dict(performance),
    }
    if created_at is not None:
        node["schema:dateCreated"] = created_at
    if self_url is not None:
        node["pe:selfUrl"] = self_url
    return node


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
    self_url: Optional[str] = None,
) -> dict:
    """Build a TRACE TRO for a certified runtime bundle.

    Artifacts in the composition: bundle manifest, data release manifest,
    certified dataset, and (when resolvable) the country model wheel.
    Certification metadata is encoded as structured ``pe:*`` fields on
    the :class:`trov:TransparentResearchPerformance` node.

    ``self_url`` is recorded on the TRO node as ``pe:selfUrl`` so a
    verifier who has only the bundle bytes can still discover the
    canonical location this TRO was published at.

    .. note::
       ``pe:compatibilityBasis`` covers the model and data layers only.
       The Python interpreter version, OS, and transitive dependency
       lockfile are not yet pinned in the TRO composition — reviewers
       who require bit-exact reproducibility of the runtime stack need
       to consult the wheel's own metadata and should flag the gap.
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
    dataset_sha256 = certified_artifact.sha256 or dataset_artifact.sha256
    if dataset_sha256 is None:
        raise ValueError(
            "Neither the country release manifest nor the data release manifest "
            f"provides a SHA256 for dataset '{certified_artifact.dataset}'."
        )

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

    bundle_manifest_hash = hashlib.sha256(
        canonical_json_bytes(country_manifest.model_dump(mode="json"))
    ).hexdigest()
    data_release_manifest_hash = hashlib.sha256(
        canonical_json_bytes(data_release_manifest.model_dump(mode="json"))
    ).hexdigest()

    model_wheel_sha, model_wheel_https = _resolve_model_wheel(
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
            "hash": dataset_sha256,
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

    composition, arrangement = _assemble_composition_and_arrangement(
        artifact_specs,
        arrangement_comment=(
            f"Certified arrangement for bundle "
            f"{country_manifest.bundle_id or country_manifest.country_id}."
        ),
    )

    effective_certification = certification or country_manifest.certification
    performance = _build_bundle_performance(
        country_manifest,
        certified_data_build_id=(
            effective_certification.data_build_id
            if effective_certification is not None
            else None
        )
        or certified_artifact.build_id
        or (
            f"{country_manifest.data_package.name}-"
            f"{country_manifest.data_package.version}"
        ),
        certification=effective_certification,
        started_at=(
            data_release_manifest.build.built_at
            if data_release_manifest.build is not None
            else country_manifest.published_at
        ),
        ended_at=country_manifest.published_at,
        emission_context=_emission_context(),
    )

    tro_node = _assemble_tro_node(
        tro_name=f"policyengine {country_manifest.country_id} certified bundle TRO",
        tro_description=(
            f"TRACE TRO for certified runtime bundle "
            f"{country_manifest.bundle_id or country_manifest.country_id} "
            f"covering the bundle manifest, the country data release "
            f"manifest, the certified dataset artifact, and the country "
            f"model wheel."
        ),
        created_at=country_manifest.published_at
        or (
            data_release_manifest.build.built_at
            if data_release_manifest.build is not None
            else None
        ),
        creator=POLICYENGINE_ORGANIZATION,
        software_version=country_manifest.policyengine_version,
        trs_comment=(
            "PolicyEngine certification workflow that pins a country model "
            "version, a country data release, and a specific dataset artifact."
        ),
        composition=composition,
        arrangement=arrangement,
        performance=performance,
        self_url=self_url,
    )

    return {"@context": TRACE_CONTEXT, "@graph": [tro_node]}


def _build_bundle_performance(
    country_manifest: CountryReleaseManifest,
    *,
    certified_data_build_id: str,
    certification: Optional[DataCertification],
    started_at: Optional[str],
    ended_at: Optional[str],
    emission_context: Mapping[str, str],
) -> dict[str, Any]:
    performance: dict[str, Any] = {
        "@id": "trp/1",
        "@type": "trov:TransparentResearchPerformance",
        "rdfs:comment": (
            f"Certification of build {certified_data_build_id} for "
            f"{country_manifest.model_package.name} "
            f"{country_manifest.model_package.version}."
        ),
        "trov:wasConductedBy": {"@id": "trs"},
        "trov:accessedArrangement": {"@id": "arrangement/1"},
    }
    if started_at is not None:
        performance["trov:startedAtTime"] = started_at
    if ended_at is not None:
        performance["trov:endedAtTime"] = ended_at
    if certification is not None:
        performance["pe:certifiedForModelVersion"] = (
            certification.certified_for_model_version
        )
        performance["pe:compatibilityBasis"] = certification.compatibility_basis
        if certification.built_with_model_version is not None:
            performance["pe:builtWithModelVersion"] = (
                certification.built_with_model_version
            )
        if certification.built_with_model_git_sha is not None:
            performance["pe:builtWithModelGitSha"] = (
                certification.built_with_model_git_sha
            )
        if certification.data_build_fingerprint is not None:
            performance["pe:dataBuildFingerprint"] = (
                certification.data_build_fingerprint
            )
        if certification.data_build_id is not None:
            performance["pe:dataBuildId"] = certification.data_build_id
        if certification.certified_by is not None:
            performance["pe:certifiedBy"] = certification.certified_by
    performance.update(emission_context)
    return performance


def serialize_trace_tro(tro: Mapping) -> bytes:
    """Serialize a TRO with the same canonical JSON used for hashing."""
    return canonical_json_bytes(tro)


def extract_bundle_tro_reference(tro: Mapping) -> dict[str, Any]:
    """Extract a compact reference to a bundle TRO for use as a simulation input.

    Locates the ``trov:TransparentResearchObject`` node explicitly rather
    than trusting ``@graph[0]`` so future TROs that embed additional
    nodes (TRS, TSA) do not break reference extraction.
    """
    graph = tro.get("@graph") or []
    node = next(
        (n for n in graph if n.get("@type") == "trov:TransparentResearchObject"),
        None,
    )
    if node is None:
        raise ValueError(
            "TRO graph does not contain a trov:TransparentResearchObject node."
        )
    composition = node.get("trov:hasComposition") or {}
    fingerprint = (
        composition.get("trov:hasFingerprint", {}).get("trov:sha256")
        if isinstance(composition, Mapping)
        else None
    )
    if fingerprint is None:
        raise ValueError("TRO is missing a composition fingerprint.")
    self_url = node.get("pe:selfUrl")
    return {
        "fingerprint": fingerprint,
        "name": node.get("schema:name"),
        "policyengine_version": (
            node.get("trov:createdWith", {}).get("schema:softwareVersion")
        ),
        "self_url": self_url,
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
    bundle_tro_url: Optional[str] = None,
) -> dict:
    """Build a per-simulation TRO chaining a bundle TRO to a results payload.

    The simulation TRO composition pins: the bundle TRO itself, the
    reform JSON (if provided), and the ``results.json`` payload. The
    ``bundle_tro_url`` field is recorded on the performance node under
    ``pe:bundleTroUrl`` so a verifier can cross-check the bundle TRO
    hash against bytes fetched from a canonical location rather than
    trusting the caller's dict.
    """
    bundle_reference = extract_bundle_tro_reference(bundle_tro)
    bundle_hash = hashlib.sha256(canonical_json_bytes(bundle_tro)).hexdigest()
    results_hash = hashlib.sha256(canonical_json_bytes(results_payload)).hexdigest()

    artifact_specs: list[dict[str, Any]] = [
        {
            "id": "bundle_tro",
            "hash": bundle_hash,
            "location": bundle_tro_location
            or bundle_tro_url
            or f"bundle.trace.tro.jsonld#{bundle_reference['fingerprint']}",
            "mime_type": "application/ld+json",
            "name": bundle_reference.get("name") or "policyengine bundle TRO",
        }
    ]
    if reform_payload is not None:
        reform_hash = hashlib.sha256(canonical_json_bytes(reform_payload)).hexdigest()
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

    simulation_slug = simulation_id or "simulation"
    composition, arrangement = _assemble_composition_and_arrangement(
        artifact_specs,
        arrangement_comment=f"Simulation arrangement for {simulation_slug}.",
    )

    performance: dict[str, Any] = {
        "@id": "trp/1",
        "@type": "trov:TransparentResearchPerformance",
        "rdfs:comment": (
            f"PolicyEngine simulation bound to bundle fingerprint "
            f"{bundle_reference['fingerprint']}."
        ),
        "trov:wasConductedBy": {"@id": "trs"},
        "trov:accessedArrangement": {"@id": "arrangement/1"},
        "pe:bundleFingerprint": bundle_reference["fingerprint"],
    }
    if bundle_tro_url is not None:
        performance["pe:bundleTroUrl"] = bundle_tro_url
    if started_at is not None or created_at is not None:
        performance["trov:startedAtTime"] = started_at or created_at
    if created_at is not None:
        performance["trov:endedAtTime"] = created_at
    performance.update(_emission_context())

    tro_node = _assemble_tro_node(
        tro_name=f"policyengine simulation TRO ({simulation_slug})",
        tro_description=(
            "TRACE TRO for a PolicyEngine simulation result. Composition "
            "pins the certified runtime bundle TRO, the reform "
            "specification (where applicable), and the results.json payload."
        ),
        created_at=created_at,
        creator=POLICYENGINE_ORGANIZATION,
        software_version=bundle_reference.get("policyengine_version"),
        trs_comment=(
            "PolicyEngine simulation that consumes a certified runtime "
            "bundle and produces a results.json payload."
        ),
        composition=composition,
        arrangement=arrangement,
        performance=performance,
    )

    return {"@context": TRACE_CONTEXT, "@graph": [tro_node]}
