"""Citable run records for population simulations.

A run record makes a hosted simulation result permanently citable: a
self-contained directory holding the reform, input, and results
payloads, the certified bundle TRO, and a per-run TRACE TRO that binds
them all by sha256. The run TRO's composition fingerprint is the
citable identifier — two records of the same run produce the same
fingerprint, and any edit to any payload changes it.

The record is written with the same canonical JSON used for hashing, so
``policyengine trace-tro-verify run.trace.tro.jsonld`` passes offline
on the directory exactly as written, and still passes years later if
the bytes were preserved.

Custom Python ``simulation_modifier`` callables cannot be certified:
the record would claim a parametric reform while arbitrary code shaped
the result. ``UncertifiableSimulationError`` refuses them instead of
emitting a false certificate.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Optional, Union

from policyengine.provenance.trace import (
    build_simulation_trace_tro,
    canonical_json_bytes,
    extract_bundle_tro_reference,
    serialize_trace_tro,
)

if TYPE_CHECKING:
    from .dynamic import Dynamic
    from .policy import Policy
    from .simulation import Simulation


class UncertifiableSimulationError(ValueError):
    """The simulation contains elements a run record cannot bind by hash."""


@dataclass(frozen=True)
class SimulationRunRecord:
    """A written run record: file paths, citable fingerprint, and the TRO."""

    paths: dict[str, Path] = field(default_factory=dict)
    composition_fingerprint: str = ""
    tro: dict = field(default_factory=dict)


def _sha256_file(path: Union[str, Path]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reform_specification(
    reform: Optional[Union[Policy, Dynamic]],
) -> Optional[dict[str, Any]]:
    """Content-determined payload for a ``Policy`` or ``Dynamic``.

    Includes only what determines the simulation: parameter paths,
    values, and effective dates, sorted for stable hashing. Identity
    fields (``id``, ``created_at``) are excluded so the same reform
    hashes identically across constructions.

    Raises :class:`UncertifiableSimulationError` when the reform
    carries a ``simulation_modifier`` callable — arbitrary Python
    cannot be bound by hash, and a record that silently dropped it
    would certify something other than what ran.
    """
    if reform is None:
        return None
    if reform.simulation_modifier is not None:
        raise UncertifiableSimulationError(
            "Cannot write a run record for a reform with a simulation_modifier "
            "callable: the modifier's behavior cannot be bound by hash, so the "
            "record would not certify what actually ran. Express the reform as "
            "parameter values, or omit the run record."
        )
    parameter_values = [
        {
            "parameter": (
                value.parameter.name if value.parameter is not None else None
            ),
            "value": value.value,
            "start_date": (
                value.start_date.isoformat() if value.start_date is not None else None
            ),
            "end_date": (
                value.end_date.isoformat() if value.end_date is not None else None
            ),
        }
        for value in reform.parameter_values
    ]
    parameter_values.sort(
        key=lambda entry: (entry["parameter"] or "", entry["start_date"] or "")
    )
    return {"name": reform.name, "parameter_values": parameter_values}


def _dataset_reference(dataset: Any) -> dict[str, Any]:
    """Bind a dataset by content hash, not by local path.

    Only the file's basename is recorded — absolute paths leak local
    usernames and directory layouts into a publishable record.
    """
    filepath = Path(dataset.filepath)
    if not filepath.exists():
        raise FileNotFoundError(
            f"Dataset file {filepath.name} does not exist; a run record must "
            "bind the actual bytes that were simulated."
        )
    return {
        "name": dataset.name,
        "file": filepath.name,
        "sha256": _sha256_file(filepath),
        "year": dataset.year,
    }


def _table_summaries(dataset: Any) -> Optional[dict[str, Any]]:
    data = getattr(dataset, "data", None)
    if data is None:
        return None
    entity_data = getattr(data, "entity_data", None)
    if entity_data is None:
        return None
    return {
        entity: {
            "rows": int(len(table)),
            "columns": sorted(str(column) for column in table.columns),
        }
        for entity, table in entity_data.items()
    }


def _scoping_payload(scoping_strategy: Any) -> Optional[dict[str, Any]]:
    if scoping_strategy is None:
        return None
    payload: dict[str, Any] = {"type": type(scoping_strategy).__name__}
    dump = getattr(scoping_strategy, "model_dump", None)
    if dump is not None:
        try:
            payload["parameters"] = dump(mode="json", exclude={"id"})
        except Exception as exc:
            raise UncertifiableSimulationError(
                f"Cannot serialize the scoping strategy into a run record: {exc}"
            ) from exc
    return payload


def build_simulation_run_record_payloads(
    simulation: Simulation,
) -> dict[str, Optional[dict[str, Any]]]:
    """Build the reform/input/results payloads a run record binds.

    Requires the simulation to have been run: the record certifies real
    output bytes, not an intention to produce them.
    """
    if simulation.output_dataset is None:
        raise ValueError(
            "Simulation has no output dataset; call ensure() (or run() and "
            "save()) before writing a run record."
        )

    reform = reform_specification(simulation.policy)
    dynamic = reform_specification(simulation.dynamic)

    input_payload: dict[str, Any] = {
        "dataset": _dataset_reference(simulation.dataset),
        "dynamic": dynamic,
        "scoping_strategy": _scoping_payload(simulation.scoping_strategy),
        "extra_variables": simulation.extra_variables or {},
    }

    output = _dataset_reference(simulation.output_dataset)
    output["tables"] = _table_summaries(simulation.output_dataset)
    results_payload = {"output_dataset": output}

    return {"reform": reform, "input": input_payload, "results": results_payload}


def write_simulation_run_record(
    simulation: Simulation,
    directory: Union[str, Path],
    *,
    bundle_tro: Optional[Mapping] = None,
    bundle_tro_url: Optional[str] = None,
    request_payload: Optional[Mapping] = None,
    runtime_environment: Optional[Mapping[str, Any]] = None,
    created_at: Optional[str] = None,
) -> SimulationRunRecord:
    """Write a self-contained, offline-verifiable run record directory.

    Files written: ``bundle.trace.tro.jsonld`` (the certified bundle
    TRO), ``reform.json`` (when the simulation has a policy),
    ``input.json``, ``results.json``, ``request.json`` (when an API
    request payload is supplied), and ``run.trace.tro.jsonld`` binding
    them all. Pass ``bundle_tro_url`` whenever a canonical published
    location for the bundle TRO exists — it lets a verifier cross-check
    the local copy against independently fetched bytes.

    ``created_at`` defaults to the simulation's creation time; pass an
    explicit ISO 8601 string to make record bytes reproducible.
    """
    if bundle_tro is None:
        if simulation.tax_benefit_model_version is None:
            raise ValueError(
                "No bundle TRO available: pass bundle_tro= or attach a "
                "tax_benefit_model_version with a bundled release manifest."
            )
        bundle_tro = simulation.tax_benefit_model_version.trace_tro

    # Build payloads (and surface refusals) before touching the filesystem.
    payloads = build_simulation_run_record_payloads(simulation)
    if created_at is None:
        created_at = simulation.created_at.isoformat()

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}

    bundle_path = directory / "bundle.trace.tro.jsonld"
    bundle_path.write_bytes(serialize_trace_tro(bundle_tro))
    paths["bundle_tro"] = bundle_path

    for key, filename in (
        ("reform", "reform.json"),
        ("input", "input.json"),
        ("results", "results.json"),
    ):
        payload = payloads[key]
        if payload is None:
            continue
        path = directory / filename
        path.write_bytes(canonical_json_bytes(payload))
        paths[key] = path
    if request_payload is not None:
        path = directory / "request.json"
        path.write_bytes(canonical_json_bytes(request_payload))
        paths["request"] = path

    tro = build_simulation_trace_tro(
        bundle_tro=bundle_tro,
        results_payload=payloads["results"],
        reform_payload=payloads["reform"],
        input_payload=payloads["input"],
        request_payload=request_payload,
        runtime_environment=runtime_environment,
        simulation_id=simulation.id,
        created_at=created_at,
        results_location="results.json",
        reform_location="reform.json",
        input_location="input.json",
        request_location="request.json",
        bundle_tro_location="bundle.trace.tro.jsonld",
        bundle_tro_url=bundle_tro_url,
    )
    tro_path = directory / "run.trace.tro.jsonld"
    tro_path.write_bytes(serialize_trace_tro(tro))
    paths["tro"] = tro_path

    fingerprint = extract_bundle_tro_reference(tro)["fingerprint"]
    return SimulationRunRecord(
        paths=paths, composition_fingerprint=fingerprint, tro=tro
    )
