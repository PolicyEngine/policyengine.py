"""Fetch-and-rehash verification of TRACE TROs.

``policyengine trace-tro-validate`` checks a TRO's *structure* against
the shipped JSON Schema. This module checks its *substance*: every
artifact in the composition is read back from its arrangement location,
rehashed, and compared against the ``trov:sha256`` the TRO claims, and
the composition fingerprint is recomputed from the artifact hashes.

A TRO is a structured claim, not a guarantee — this is the query layer
that turns the claim into something a third party can check without
trusting the emitter. Locations resolve in two ways:

- ``https://`` URLs are fetched over the network.
- Relative paths resolve against ``base_dir`` (for
  ``verify_trace_tro_path``, the TRO file's own directory), which is
  how self-contained run-record directories verify offline. Paths that
  escape ``base_dir`` are refused.

Artifacts that cannot be fetched (restricted-access data, dead hosts)
are reported as ``unfetchable`` and fail verification unless explicitly
skipped — silence is not verification.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .trace import compute_trace_composition_fingerprint

_ARTIFACT_ID_SEPARATOR = "/artifact/"


@dataclass(frozen=True)
class ArtifactCheck:
    """Verification outcome for one composition artifact."""

    artifact_id: str
    expected_sha256: str
    location: Optional[str]
    status: str  # "ok" | "mismatch" | "unfetchable" | "skipped"
    detail: Optional[str] = None


@dataclass(frozen=True)
class TROVerificationReport:
    """Outcome of verifying a TRO's composition against its locations."""

    fingerprint_status: str  # "ok" | "mismatch"
    artifacts: list[ArtifactCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.fingerprint_status == "ok" and all(
            check.status in ("ok", "skipped") for check in self.artifacts
        )


def _default_fetch(url: str, *, timeout: float = 60.0) -> bytes:
    import requests

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def _find_tro_node(tro: Mapping) -> Mapping:
    graph = tro.get("@graph") or []
    node = next(
        (n for n in graph if n.get("@type") == "trov:TransparentResearchObject"),
        None,
    )
    if node is None:
        raise ValueError(
            "TRO graph does not contain a trov:TransparentResearchObject node."
        )
    return node


def _short_artifact_id(full_id: str) -> str:
    if _ARTIFACT_ID_SEPARATOR in full_id:
        return full_id.split(_ARTIFACT_ID_SEPARATOR, 1)[1]
    return full_id


def _artifact_locations(node: Mapping) -> dict[str, str]:
    """Map full artifact ``@id`` to its first arrangement location."""
    locations: dict[str, str] = {}
    for arrangement in node.get("trov:hasArrangement") or []:
        for entry in arrangement.get("trov:hasArtifactLocation") or []:
            artifact_ref = (entry.get("trov:hasArtifact") or {}).get("@id")
            location = entry.get("trov:hasLocation")
            if artifact_ref and location and artifact_ref not in locations:
                locations[artifact_ref] = location
    return locations


def _resolve_local(location: str, base_dir: Optional[Path]) -> Path:
    """Resolve a relative artifact location inside ``base_dir``.

    Absolute paths and ``..`` traversal are refused: a TRO must not be
    able to direct a verifier at arbitrary files on the host.
    """
    if base_dir is None:
        raise ValueError("no base directory for relative artifact locations")
    candidate = Path(location)
    if candidate.is_absolute():
        raise ValueError(f"absolute artifact location refused: {location}")
    resolved = (base_dir / candidate).resolve()
    base_resolved = base_dir.resolve()
    if not resolved.is_relative_to(base_resolved):
        raise ValueError(f"artifact location escapes the record directory: {location}")
    return resolved


def _artifact_bytes(
    location: str,
    *,
    base_dir: Optional[Path],
    fetch: Callable[[str], bytes],
) -> bytes:
    if location.startswith("https://"):
        return fetch(location)
    if location.startswith(("http://", "file://", "hf://")):
        raise ValueError(f"unsupported artifact location scheme: {location}")
    return _resolve_local(location, base_dir).read_bytes()


def verify_trace_tro(
    tro: Mapping,
    *,
    base_dir: Optional[Path] = None,
    fetch: Optional[Callable[[str], bytes]] = None,
    skip: Optional[Iterable[str]] = None,
) -> TROVerificationReport:
    """Rehash every composition artifact and the composition fingerprint.

    ``skip`` takes short artifact ids (the part after ``/artifact/``,
    e.g. ``dataset``) for artifacts a verifier knowingly cannot fetch,
    such as restricted-access inputs. Skipped artifacts do not fail the
    report, but they are listed so the verification is honest about its
    coverage.
    """
    fetch = fetch or _default_fetch
    skip_set = set(skip or ())
    node = _find_tro_node(tro)
    composition = node.get("trov:hasComposition") or {}
    artifacts = composition.get("trov:hasArtifact") or []
    locations = _artifact_locations(node)

    claimed_fingerprint = (composition.get("trov:hasFingerprint") or {}).get(
        "trov:sha256"
    )
    recomputed = compute_trace_composition_fingerprint(
        [artifact.get("trov:sha256") for artifact in artifacts]
    )
    fingerprint_status = "ok" if recomputed == claimed_fingerprint else "mismatch"

    checks: list[ArtifactCheck] = []
    for artifact in artifacts:
        full_id = artifact.get("@id", "")
        short_id = _short_artifact_id(full_id)
        expected = artifact.get("trov:sha256")
        location = locations.get(full_id)
        if short_id in skip_set:
            checks.append(ArtifactCheck(short_id, expected, location, "skipped"))
            continue
        if location is None:
            checks.append(
                ArtifactCheck(
                    short_id,
                    expected,
                    None,
                    "unfetchable",
                    "no arrangement location for artifact",
                )
            )
            continue
        try:
            payload = _artifact_bytes(location, base_dir=base_dir, fetch=fetch)
        except Exception as exc:
            checks.append(
                ArtifactCheck(short_id, expected, location, "unfetchable", str(exc))
            )
            continue
        actual = hashlib.sha256(payload).hexdigest()
        if actual == expected:
            checks.append(ArtifactCheck(short_id, expected, location, "ok"))
        else:
            checks.append(
                ArtifactCheck(
                    short_id,
                    expected,
                    location,
                    "mismatch",
                    f"sha256 {actual} != claimed {expected}",
                )
            )

    return TROVerificationReport(
        fingerprint_status=fingerprint_status, artifacts=checks
    )


def verify_trace_tro_path(
    path: Path | str,
    *,
    fetch: Optional[Callable[[str], bytes]] = None,
    skip: Optional[Iterable[str]] = None,
) -> TROVerificationReport:
    """Verify a TRO file, resolving relative locations against its directory."""
    import json

    path = Path(path)
    tro = json.loads(path.read_text())
    return verify_trace_tro(tro, base_dir=path.parent, fetch=fetch, skip=skip)
