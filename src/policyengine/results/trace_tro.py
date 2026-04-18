"""Per-simulation TRACE TRO for results.json payloads.

The certified-bundle TRO pins the country model, data package, and
dataset artifact together. A simulation TRO chains that bundle to a
specific reform + ``results.json`` payload so a published result can
be cited with an immutable composition fingerprint.

See :mod:`policyengine.core.trace_tro` for the bundle-level layer.
"""

from __future__ import annotations

import json
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
) -> dict:
    """Build a per-simulation TRO for a ``ResultsJson`` instance.

    Args:
        results: The validated results payload.
        bundle_tro: A bundle-level TRACE TRO (see
            :func:`policyengine.core.trace_tro.build_trace_tro_from_release_bundle`).
        reform_payload: Optional reform JSON to include as a hashed artifact.
        reform_name: Optional display name for the reform.
        simulation_id: Optional identifier used in the TRO's ``schema:name``.
        results_location: Optional URI or path for the ``results.json`` file.
        reform_location: Optional URI or path for the reform JSON.
        bundle_tro_location: Optional URI or path for the bundle TRO.

    Returns:
        The TRO as a ``dict``. Serialize with
        :func:`policyengine.core.trace_tro.serialize_trace_tro`.
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
    )


def write_results_with_trace_tro(
    results: ResultsJson,
    results_path: Union[str, Path],
    *,
    bundle_tro: Mapping,
    reform_payload: Optional[Mapping] = None,
    reform_name: Optional[str] = None,
    tro_suffix: str = ".trace.tro.jsonld",
    bundle_tro_path: Optional[Union[str, Path]] = None,
) -> dict[str, Path]:
    """Write ``results.json`` and a sibling per-simulation TRACE TRO.

    The TRO is written next to the results file with the given suffix
    appended to the results filename stem. Returns a dict with ``results``
    and ``tro`` paths.
    """
    results_path = Path(results_path)
    results.write(results_path)

    if bundle_tro_path is not None:
        bundle_tro_path = Path(bundle_tro_path)
        bundle_tro_location: Optional[str] = bundle_tro_path.name
    else:
        bundle_tro_location = None

    tro = build_results_trace_tro(
        results,
        bundle_tro=bundle_tro,
        reform_payload=reform_payload,
        reform_name=reform_name,
        results_location=results_path.name,
        bundle_tro_location=bundle_tro_location,
    )
    tro_path = results_path.with_suffix(tro_suffix)
    tro_path.write_bytes(serialize_trace_tro(tro))

    written: dict[str, Path] = {"results": results_path, "tro": tro_path}

    if bundle_tro_path is not None:
        bundle_tro_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_tro_path.write_text(
            json.dumps(bundle_tro, indent=2, sort_keys=True) + "\n"
        )
        written["bundle_tro"] = bundle_tro_path

    return written
