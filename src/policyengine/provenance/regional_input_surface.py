"""Audit regional H5 bytes against the exact installed UK country model.

The set comparison ports Microcosm PR #1348's handoff comparison, replacing
its older-model inventory proxy with the columns actually stored in every
artifact and period. Country-model input moves are read from that installed
model's constructor, so an alias cannot make a supplied input look defaulted.
No household values are included in the resulting audit.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import re
import textwrap
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from policyengine.provenance.manifest import (
    RegionalInputArtifactEvidence,
    RegionalInputSurfaceEvidence,
)

UK_ENTITIES = ("person", "benunit", "household")


class RegionalInputSurfaceError(ValueError):
    """A complete, byte-bound regional surface cannot be established."""


def _names(values: list[str], label: str) -> set[str]:
    if not values or any(
        not isinstance(value, str) or not value.strip() or value != value.strip()
        for value in values
    ):
        raise RegionalInputSurfaceError(f"{label} must contain nonblank names.")
    names = set(values)
    if len(names) != len(values):
        raise RegionalInputSurfaceError(f"{label} contains duplicate names.")
    return names


def compare_input_surface(
    artifacts: dict[str, RegionalInputArtifactEvidence],
    model_variables: list[str],
    model_inputs: list[str],
    input_aliases: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Recompute losses and every default, including defaults in just one year.

    Inputs supplied by the model's unconditional ``move_values`` calls use the
    destination name after the move. Raw columns still have to be variables
    defined by the target model. Every artifact and period must pass: the
    union of supplied columns cannot hide a missing input in another period.
    """
    variables = _names(model_variables, "model_variables")
    inputs = _names(model_inputs, "model_inputs")
    if not inputs <= variables:
        raise RegionalInputSurfaceError("model_inputs must be model_variables.")
    aliases = input_aliases or {}
    for donor, target in aliases.items():
        if (
            donor not in variables
            or target not in inputs
            or donor == target
            or target in aliases
        ):
            raise RegionalInputSurfaceError(
                f"Unsupported input alias {donor!r} -> {target!r}."
            )
    if not artifacts:
        raise RegionalInputSurfaceError("No regional artifact columns measured.")
    dropped: set[str] = set()
    defaulted: set[str] = set()
    for name, artifact in artifacts.items():
        columns = _names(artifact.columns, f"{name} columns")
        if not artifact.columns_by_period:
            raise RegionalInputSurfaceError(f"{name} has no measured periods.")
        periods = []
        for period, period_columns in artifact.columns_by_period.items():
            if not re.fullmatch(r"[0-9]{4}", period):
                raise RegionalInputSurfaceError(
                    f"{name} has an invalid period {period!r}."
                )
            periods.append(_names(period_columns, f"{name}/{period} columns"))
        if set().union(*periods) != columns:
            raise RegionalInputSurfaceError(
                f"{name} columns must equal the union of columns_by_period."
            )
        for supplied in periods:
            dropped.update(supplied - variables)
            effective = set(supplied)
            for donor, target in aliases.items():
                if donor in effective:
                    effective.remove(donor)
                    effective.add(target)
            defaulted.update(inputs - effective)
    return {
        "dropped_columns": sorted(dropped),
        "defaulted_inputs": sorted(defaulted),
    }


def _input_aliases(simulation_class: Any) -> dict[str, str]:
    """Read unconditional literal moves; refuse unsupported dynamic semantics.

    policyengine-uk has no public alias inventory. Its public Simulation
    constructor declares the input moves. Reading that source avoids running
    a simulation or encoding one version's aliases as a permanent allowlist.
    """
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(simulation_class.__init__)))
    except (OSError, TypeError, SyntaxError) as exc:
        raise RegionalInputSurfaceError(
            "Cannot inspect the installed UK Simulation input aliases."
        ) from exc
    constructor = tree.body[0]
    if not isinstance(constructor, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise RegionalInputSurfaceError("Cannot locate the UK Simulation constructor.")
    unconditional = {
        id(statement.value)
        for statement in constructor.body
        if isinstance(statement, ast.Expr)
    }
    aliases: dict[str, str] = {}
    for node in ast.walk(constructor):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
            and node.func.attr == "move_values"
        ):
            continue
        if (
            id(node) not in unconditional
            or len(node.args) != 2
            or node.keywords
            or any(
                not isinstance(argument, ast.Constant)
                or not isinstance(argument.value, str)
                for argument in node.args
            )
        ):
            raise RegionalInputSurfaceError(
                "UK Simulation has a conditional or dynamic move_values input alias; "
                "an explicit audit of its semantics is required."
            )
        donor = str(node.args[0].value)  # type: ignore[attr-defined]
        target = str(node.args[1].value)  # type: ignore[attr-defined]
        if donor in aliases:
            raise RegionalInputSurfaceError(f"Duplicate move_values alias {donor!r}.")
        aliases[donor] = target
    return aliases


def _model_surface(model_version: str) -> tuple[list[str], list[str], dict[str, str]]:
    try:
        installed = version("policyengine-uk")
    except PackageNotFoundError as exc:
        raise RegionalInputSurfaceError(
            "Install the exact policyengine-uk target first."
        ) from exc
    if installed != model_version:
        raise RegionalInputSurfaceError(
            f"Installed policyengine-uk {installed} differs from requested {model_version}."
        )
    # Keep country-model loading out of certification's evidence-validation path.
    import policyengine_uk

    system = policyengine_uk.CountryTaxBenefitSystem()
    variables = sorted(system.variables)
    inputs = sorted(
        name
        for name, variable in system.variables.items()
        if variable.is_input_variable()
    )
    return variables, inputs, _input_aliases(policyengine_uk.Simulation)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hdf_columns(path: Path) -> dict[str, list[str]]:
    import pandas as pd

    try:
        with pd.HDFStore(path, mode="r") as store:
            keys = set(store.keys())
            flat = {f"/{entity}" for entity in UK_ENTITIES} & keys
            nested = {
                key
                for key in keys
                if any(key.startswith(f"/{entity}/") for entity in UK_ENTITIES)
            }
            if flat and nested:
                raise RegionalInputSurfaceError(
                    "H5 mixes single-year and multi-year entity keys."
                )
            entity_keys: dict[str, dict[str, str]] = {}
            if flat:
                if "/time_period" not in keys:
                    raise RegionalInputSurfaceError(
                        "Single-year H5 requires /time_period."
                    )
                metadata = store.select("/time_period")
                values = metadata.to_numpy().ravel().tolist()
                if len(values) != 1 or not re.fullmatch(r"[0-9]{4}", str(values[0])):
                    raise RegionalInputSurfaceError(
                        "H5 /time_period must name one year."
                    )
                entity_keys[str(values[0])] = {
                    entity: f"/{entity}"
                    for entity in UK_ENTITIES
                    if f"/{entity}" in flat
                }
            else:
                for key in sorted(nested):
                    parts = key.strip("/").split("/")
                    if len(parts) != 2 or not re.fullmatch(r"[0-9]{4}", parts[1]):
                        raise RegionalInputSurfaceError(
                            f"Invalid H5 entity period key {key!r}."
                        )
                    entity_keys.setdefault(parts[1], {})[parts[0]] = key
            if not entity_keys:
                raise RegionalInputSurfaceError("H5 has no UK entity periods.")
            columns_by_period = {}
            for period, entities in sorted(entity_keys.items()):
                missing = set(UK_ENTITIES) - set(entities)
                if missing:
                    raise RegionalInputSurfaceError(
                        f"H5 period {period} is missing entity tables: {sorted(missing)}."
                    )
                columns: set[str] = set()
                for entity in UK_ENTITIES:
                    # This obtains the same column metadata for fixed and table
                    # stores without selecting household or person rows.
                    frame = store.select(entities[entity], start=0, stop=0)
                    columns.update(
                        _names(list(frame.columns), f"{entity}/{period} columns")
                    )
                columns_by_period[period] = sorted(columns)
            return columns_by_period
    except RegionalInputSurfaceError:
        raise
    except (OSError, KeyError, ValueError, ImportError) as exc:
        raise RegionalInputSurfaceError(
            f"Cannot read H5 entity metadata from {path.name}."
        ) from exc


def measure_regional_input_surface(
    regional_manifest_uri: str,
    artifact_paths: dict[str, Path],
    model_version: str,
    audited_by: str,
    limitations: list[str],
    token: str | None = None,
) -> RegionalInputSurfaceEvidence:
    """Create an audit from actual H5 columns and an exact installed UK model.

    The operator supplies local files named by the immutable regional release.
    Every microdata H5 must be measured and match its manifest's SHA-256 both
    before and after metadata inspection. This reads no unit values for output.
    """
    # Imported lazily: the certification gate reuses compare_input_surface.
    from policyengine.provenance.certification import fetch_release_manifest

    if (
        not audited_by.strip()
        or not limitations
        or any(not item.strip() for item in limitations)
    ):
        raise RegionalInputSurfaceError(
            "An auditor and nonblank limitations are required."
        )
    manifest, manifest_sha256, parts = fetch_release_manifest(
        regional_manifest_uri, token=token
    )
    expected = {
        name: artifact
        for name, artifact in manifest.artifacts.items()
        if artifact.kind == "microdata" and Path(artifact.path).suffix.lower() == ".h5"
    }
    if not expected or set(artifact_paths) != set(expected):
        raise RegionalInputSurfaceError(
            "Supplied artifact paths must exactly cover the regional microdata H5 artifacts: "
            f"{sorted(expected)}."
        )
    variables, inputs, aliases = _model_surface(model_version)
    artifacts = {}
    for name, artifact in sorted(expected.items()):
        path = Path(artifact_paths[name])
        if not artifact.sha256:
            raise RegionalInputSurfaceError(
                f"Artifact {name!r} has no manifest sha256."
            )
        before = _sha256_file(path)
        if before != artifact.sha256:
            raise RegionalInputSurfaceError(
                f"Artifact {name!r} bytes differ from its manifest sha256."
            )
        periods = _hdf_columns(path)
        after = _sha256_file(path)
        if after != before:
            raise RegionalInputSurfaceError(
                f"Artifact {name!r} bytes changed during metadata inspection."
            )
        artifacts[name] = RegionalInputArtifactEvidence(
            repo_id=artifact.repo_id,
            repo_type=artifact.repo_type or parts["repo_type"],
            path=artifact.path,
            revision=artifact.revision,
            sha256=after,
            columns=sorted(
                {column for columns in periods.values() for column in columns}
            ),
            columns_by_period=periods,
        )
    comparison = compare_input_surface(artifacts, variables, inputs, aliases)
    if comparison["dropped_columns"]:
        raise RegionalInputSurfaceError(
            f"Dropped regional input columns refuse acceptance: {comparison['dropped_columns']}."
        )
    return RegionalInputSurfaceEvidence(
        regional_manifest_uri=regional_manifest_uri,
        regional_manifest_sha256=manifest_sha256,
        model_package="policyengine-uk",
        model_version=model_version,
        artifacts=artifacts,
        model_variables=variables,
        model_inputs=inputs,
        input_aliases=aliases,
        dropped_columns=comparison["dropped_columns"],
        defaulted_inputs=comparison["defaulted_inputs"],
        audited_by=audited_by,
        limitations=limitations,
    )
