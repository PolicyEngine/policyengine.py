"""The capital gains realisation response a UK run applies.

policyengine-uk scales realised capital gains in response to a reform, at an
elasticity set under ``gov.simulation.capital_gains_responses``. The default
is the model's, so it can change between model releases, and a caller can
change it through a policy, a dynamic or a reform dict. Each UK run records
the response it applied, so a result says which assumption it was
calculated under and a saved result is not reused under another:

- ``model``: the policyengine-uk release that resolved it;
- ``resolved``: the assumption itself, as policyengine-uk's
  ``capital_gains_response_assumption`` reports it after every reform and
  modifier (the convention, the elasticities for main-rate gains and for
  gains qualifying for Business Asset Disposal Relief, the MTR elasticity,
  the separate relief switch, and whether each is the default, the caller's
  override, or set to zero for an MTR elasticity); ``None`` where the
  installed release has no such report;
- ``request``: the caller's explicit settings under that path, in the order
  they apply, and their digest. Changes a simulation modifier makes are not
  listed, as run records do not describe modifiers.

The record is stored with the output dataset, written into a saved output
file, and returned with a run's release bundle, run record, household
result (``provenance``) and managed microsimulation bundle.
"""

from __future__ import annotations

import datetime
import hashlib
import importlib.metadata
import json
from collections.abc import Iterable
from typing import Any, Optional

import pandas as pd

RECORD_KEY = "capital_gains_responses"
#: The output file key the record is written under.
FILE_KEY = "policyengine_uk_capital_gains_responses"
SCHEMA_VERSION = 1
RESPONSE_SETTINGS = "gov.simulation.capital_gains_responses"
# Changes to how settings are listed or digested change this, so outputs
# saved under an earlier listing are not reused.
REQUEST_REVISION = 1


def _date(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        value = value.date()
    return value.isoformat()


def _value(value) -> Any:
    if isinstance(value, bool):
        return value
    if hasattr(value, "item"):  # numpy scalars
        value = value.item()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return value


def requested_settings(sources: Iterable[tuple[str, Any]]) -> list[list]:
    """The caller's explicit response settings, in the order they apply.

    ``sources`` gives each ``(name, parameter_values)`` applied in turn (a
    policy's before a dynamic's). Each setting is listed as
    ``[parameter, start, end, value, source]``.
    """
    settings = []
    for source, parameter_values in sources:
        for parameter_value in parameter_values or []:
            name = parameter_value.parameter.name
            if name != RESPONSE_SETTINGS and not name.startswith(
                RESPONSE_SETTINGS + "."
            ):
                continue
            settings.append(
                [
                    name,
                    _date(parameter_value.start_date),
                    _date(parameter_value.end_date),
                    _value(parameter_value.value),
                    source,
                ]
            )
    return settings


def request_digest(settings: list[list]) -> Optional[str]:
    """The SHA-256 of the settings, or None when there are none."""
    if not settings:
        return None
    payload = json.dumps(
        {"revision": REQUEST_REVISION, "settings": settings},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def request(sources: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    """The explicit settings ``sources`` request, with their digest."""
    settings = requested_settings(sources)
    return {"settings": settings, "digest": request_digest(settings)}


def simulation_request(simulation) -> dict[str, Any]:
    """The explicit settings a population simulation requests."""
    return request(
        (
            ("policy", getattr(simulation.policy, "parameter_values", None)),
            ("dynamic", getattr(simulation.dynamic, "parameter_values", None)),
        )
    )


def installed_model_version() -> Optional[str]:
    try:
        return importlib.metadata.version("policyengine-uk")
    except importlib.metadata.PackageNotFoundError:
        return None


def resolve(microsimulation, year) -> Optional[dict[str, Any]]:
    """The response a policyengine-uk simulation applies in ``year``.

    None where the installed policyengine-uk does not report it. Raises
    policyengine-uk's ``ValueError`` on settings that conflict.
    """
    try:
        from policyengine_uk.utils.capital_gains import (
            capital_gains_response_assumption,
        )
    except ImportError:
        return None
    return capital_gains_response_assumption(microsimulation, int(year)).to_dict()


def build_record(
    microsimulation, year, request: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """The record of the response a run applies, after every modifier."""
    return {
        "schema_version": SCHEMA_VERSION,
        "model": {"package": "policyengine-uk", "version": installed_model_version()},
        "period": str(int(year)),
        "resolved": resolve(microsimulation, year),
        "request": request,
    }


def managed_records(microsimulation) -> dict[str, Any]:
    """Records for each year of a managed microsimulation's dataset.

    The managed helper passes ``reform=`` to policyengine-uk unchanged, so no
    request is listed. Settings that conflict are recorded as an error here,
    and raise when the response is calculated, as in a direct run.
    """
    years = getattr(getattr(microsimulation, "dataset", None), "years", None) or [
        microsimulation.default_calculation_period
    ]
    records = {}
    for year in years:
        try:
            records[str(int(year))] = build_record(microsimulation, year, None)
        except ValueError as error:
            records[str(int(year))] = {"error": str(error)}
    return records


def write_record(store: pd.HDFStore, record: dict[str, Any]) -> None:
    """Write the record into an open output file."""
    store.put(FILE_KEY, pd.Series([json.dumps(record, sort_keys=True)]))


def read_record(store: pd.HDFStore) -> Optional[dict[str, Any]]:
    """The record an open output file holds, or None."""
    if f"/{FILE_KEY}" not in store.keys():
        return None
    return json.loads(store[FILE_KEY].iloc[0])


def saved_record_problem(
    record: Optional[dict[str, Any]], request: dict[str, Any]
) -> Optional[str]:
    """Why a saved output's record rules out reusing it, or None."""
    if record is None:
        return (
            "it predates the record of its capital gains realisation response "
            "(it has none)"
        )
    if record.get("schema_version") != SCHEMA_VERSION:
        return "its capital gains response record has another schema version"
    saved_version = (record.get("model") or {}).get("version")
    if saved_version != installed_model_version():
        return (
            f"it was calculated with policyengine-uk {saved_version}, not the "
            f"installed {installed_model_version()}, whose default capital "
            "gains response may differ"
        )
    if (record.get("request") or {}).get("digest") != request["digest"]:
        return "it was calculated under other capital gains response settings"
    return None
