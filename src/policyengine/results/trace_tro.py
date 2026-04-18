"""Per-simulation TRACE TRO for results.json payloads.

The certified-bundle TRO pins the country model, data package, and
dataset artifact together. A simulation TRO chains that bundle to a
specific reform + ``results.json`` payload so a published result can
be cited with an immutable composition fingerprint.

See :mod:`policyengine.core.trace_tro` for the bundle-level layer.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Optional, Union

from policyengine.core.trace_tro import (
    build_simulation_trace_tro,
    serialize_trace_tro,
)

from .schema import ResultsJson


def build_results_trace_tro(
    results: ResultsJson,
    *,
    bundle_tro: Mapping,
    reform_payload: Optional[Mapping] = None,
    reform_name: Optional[str] = None,
    simulation_id: Optional[str] = None,
    results_location: Optional[str] = None,
    reform_location: Optional[str] = None,
    bundle_tro_location: Optional[str] = None,
    bundle_tro_url: Optional[str] = None,
) -> dict:
    """Build a per-simulation TRO for a ``ResultsJson`` instance.

    ``bundle_tro_url`` should point to a canonical, immutable location
    for the bundle TRO (e.g. a GitHub release raw URL). It is recorded
    on the performance node under ``pe:bundleTroUrl`` so a verifier can
    fetch that URL, recompute its sha256, and confirm it matches the
    bundle artifact hash in this TRO's composition. Without this
    anchor, the bundle reference is only as trustworthy as the caller.
    """
    slug = simulation_id or (results.metadata.slug or results.metadata.title)
    return build_simulation_trace_tro(
        bundle_tro=bundle_tro,
        results_payload=results.model_dump(mode="json"),
        reform_payload=reform_payload,
        reform_name=reform_name,
        simulation_id=slug,
        created_at=results.metadata.generated_at,
        results_location=results_location,
        reform_location=reform_location,
        bundle_tro_location=bundle_tro_location,
        bundle_tro_url=bundle_tro_url,
    )


def write_results_with_trace_tro(
    results: ResultsJson,
    results_path: Union[str, Path],
    *,
    bundle_tro: Mapping,
    bundle_tro_url: str,
    reform_payload: Optional[Mapping] = None,
    reform_name: Optional[str] = None,
    tro_suffix: str = ".trace.tro.jsonld",
) -> dict[str, Path]:
    """Write ``results.json`` and a sibling per-simulation TRACE TRO.

    ``bundle_tro_url`` is required: a published simulation TRO must
    point at a canonical, immutable URL for the bundle TRO so a
    verifier can fetch and rehash it independently of the caller.
    """
    results_path = Path(results_path)
    results.write(results_path)

    tro = build_results_trace_tro(
        results,
        bundle_tro=bundle_tro,
        reform_payload=reform_payload,
        reform_name=reform_name,
        results_location=results_path.name,
        bundle_tro_location=bundle_tro_url,
        bundle_tro_url=bundle_tro_url,
    )
    tro_path = results_path.with_suffix(tro_suffix)
    tro_path.write_bytes(serialize_trace_tro(tro))

    return {"results": results_path, "tro": tro_path}
