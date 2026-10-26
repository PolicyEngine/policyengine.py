"""Audit regional H5 bytes against their build model and the exact UK target.

A local-area release keeps serving area runs after the national bundle moves
to a newer policyengine-uk. The audit compares the columns actually stored in
every artifact and period with two models: the release's build model, which
its manifest records (``build.built_with_model_package`` and
``build.built_with_core_package``), and the installed target model. As in
Microcosm PR #1348's handoff comparison, the build model is the baseline:

- **dropped**: stored columns the build model defines and the target model
  does not. The target's loaders skip them, so they refuse acceptance.
- **never modelled**: stored columns neither model defines, such as
  Microcosm's area codes, build and source ids, clone indices and SPI donor
  fields. No model ever loaded them, so they are recorded as information.
- **defaulted**: target inputs a period does not store, after the target's
  input aliases, that were not inputs of the build model. Area runs default
  them where the build model did not.

Columns neither model defines, and inputs absent under both, are not changes.
The build model is read in a throwaway ``uv run`` environment, so the audit
needs ``uv`` and PyPI. Input moves are read from the installed target model's
constructor, so an alias cannot make a supplied input look defaulted. No
household values are included in the resulting audit.

policyengine-uk 2.147.2 silently skips unknown columns in both dataset loaders;
the audit must detect that loss before certification. See the ``continue``
branches in ``build_from_dataset`` and ``build_from_multi_year_dataset``:
https://github.com/PolicyEngine/policyengine-uk/blob/fe0b99a36bd309a722b19937345e34290cb6dd73/policyengine_uk/simulation.py#L1113-L1127
https://github.com/PolicyEngine/policyengine-uk/blob/fe0b99a36bd309a722b19937345e34290cb6dd73/policyengine_uk/simulation.py#L1186-L1196
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import re
import subprocess
import textwrap
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

from policyengine.provenance.manifest import (
    DataReleaseManifest,
    RegionalInputArtifactEvidence,
    RegionalInputSurfaceEvidence,
)

UK_ENTITIES = ("person", "benunit", "household")
#: The interpreter of the throwaway environment that reads the build model.
BUILD_MODEL_PYTHON = "3.13"
#: The caller's uv project settings, which must not reach that environment.
BUILD_MODEL_STRIPPED_ENV = frozenset(
    {"UV_FROZEN", "UV_PROJECT_ENVIRONMENT", "VIRTUAL_ENV"}
)
#: Runs in the build model's environment: the model API ``_model_surface``
#: uses, and the package versions it actually imported.
BUILD_MODEL_PROBE = """
import json
from importlib.metadata import version

import policyengine_uk

system = policyengine_uk.CountryTaxBenefitSystem()
print(json.dumps({
    "model_version": version("policyengine-uk"),
    "core_version": version("policyengine-core"),
    "variables": sorted(system.variables),
    "inputs": sorted(
        name
        for name, variable in system.variables.items()
        if variable.is_input_variable()
    ),
}))
"""


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
    *,
    build_model_variables: list[str],
    build_model_inputs: list[str],
) -> dict[str, list[str]]:
    """Recompute dropped, never-modelled and defaulted names per period.

    ``dropped_columns`` are stored columns the build model defines and the
    target model does not. ``never_modelled_columns`` are stored columns
    neither model defines. ``defaulted_inputs`` are target inputs a period
    does not supply that were not inputs of the build model. Inputs supplied
    by the target's unconditional ``move_values`` calls use the destination
    name after the move. Every artifact and period must pass: the union of
    supplied columns cannot hide a missing input in another period.
    """
    variables = _names(model_variables, "model_variables")
    inputs = _names(model_inputs, "model_inputs")
    if not inputs <= variables:
        raise RegionalInputSurfaceError("model_inputs must be model_variables.")
    build_variables = _names(build_model_variables, "build_model_variables")
    build_inputs = _names(build_model_inputs, "build_model_inputs")
    if not build_inputs <= build_variables:
        raise RegionalInputSurfaceError(
            "build_model_inputs must be build_model_variables."
        )
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
    never_modelled: set[str] = set()
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
            dropped.update((supplied & build_variables) - variables)
            never_modelled.update(supplied - build_variables - variables)
            effective = set(supplied)
            for donor, target in aliases.items():
                if donor in effective:
                    effective.remove(donor)
                    effective.add(target)
            defaulted.update((inputs - effective) - build_inputs)
    return {
        "dropped_columns": sorted(dropped),
        "never_modelled_columns": sorted(never_modelled),
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


def regional_build_versions(manifest: DataReleaseManifest) -> tuple[str, str]:
    """Return the regional release's build model and core: the audit baseline.

    A release that records neither, or records other packages, refuses: there
    is no model to tell a dropped column from one no model ever defined.
    """
    build = manifest.build
    model = build.built_with_model_package if build is not None else None
    core = build.built_with_core_package if build is not None else None
    if model is None or core is None:
        raise RegionalInputSurfaceError(
            "The regional manifest records no build model and core versions "
            "(build.built_with_model_package and build.built_with_core_package), "
            "so the audit has no baseline."
        )
    if model.name != "policyengine-uk" or core.name != "policyengine-core":
        raise RegionalInputSurfaceError(
            f"The regional release was built with {model.name} and {core.name}, "
            "not policyengine-uk and policyengine-core."
        )
    for package in (model, core):
        try:
            Version(package.version)
        except InvalidVersion as exc:
            raise RegionalInputSurfaceError(
                f"The regional manifest's {package.name} build version "
                f"{package.version!r} is not a version."
            ) from exc
    return model.version, core.version


def _build_model_surface(
    model_version: str,
    core_version: str,
    run: Callable[..., Any] | None = None,
) -> tuple[list[str], list[str]]:
    """Read the build model's variables and inputs in a throwaway environment.

    ``uv run --no-project`` installs exactly the two pins from PyPI, without
    the caller's uv project settings. The probe reports the versions it
    imported, and any other resolution refuses.
    """
    run = run if run is not None else subprocess.run
    label = f"policyengine-uk {model_version} with policyengine-core {core_version}"
    command = [
        "uv",
        "run",
        "--no-project",
        "--python",
        BUILD_MODEL_PYTHON,
        "--with",
        f"policyengine-uk=={model_version}",
        "--with",
        f"policyengine-core=={core_version}",
        "python",
        "-I",
        "-c",
        BUILD_MODEL_PROBE,
    ]
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in BUILD_MODEL_STRIPPED_ENV
    }
    try:
        result = run(command, capture_output=True, text=True, check=True, env=env)
    except subprocess.CalledProcessError as exc:
        detail = " | ".join((exc.stderr or "").strip().splitlines()[-5:])
        raise RegionalInputSurfaceError(
            f"Cannot read the build model {label}: {detail or exc}"
        ) from exc
    except OSError as exc:
        raise RegionalInputSurfaceError(
            f"Cannot run uv to read the build model {label}."
        ) from exc
    try:
        surface = json.loads((result.stdout or "").strip().splitlines()[-1])
    except (IndexError, ValueError) as exc:
        raise RegionalInputSurfaceError(
            f"The probe of the build model {label} printed no surface."
        ) from exc
    if not isinstance(surface, dict):
        raise RegionalInputSurfaceError(
            f"The probe of the build model {label} printed no surface."
        )
    resolved = (surface.get("model_version"), surface.get("core_version"))
    if resolved != (model_version, core_version):
        raise RegionalInputSurfaceError(
            f"The build-model probe resolved policyengine-uk {resolved[0]} with "
            f"policyengine-core {resolved[1]}, not {label}."
        )
    variables, inputs = surface.get("variables"), surface.get("inputs")
    if not isinstance(variables, list) or not isinstance(inputs, list):
        raise RegionalInputSurfaceError(
            f"The probe of the build model {label} printed no variable lists."
        )
    return (
        sorted(_names(variables, "build_model_variables")),
        sorted(_names(inputs, "build_model_inputs")),
    )


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
    *,
    run: Callable[..., Any] | None = None,
) -> RegionalInputSurfaceEvidence:
    """Audit actual H5 columns against the build model and the exact target.

    The operator supplies local files named by the immutable regional release.
    Every microdata H5 must be measured and match its manifest's SHA-256 both
    before and after metadata inspection. The installed policyengine-uk must
    be ``model_version``. The build model and core named by the manifest are
    read in a throwaway ``uv run`` environment through ``run``
    (``subprocess.run`` by default). Dropped columns refuse. This reads no
    unit values for output.
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
    build_model_version, build_core_version = regional_build_versions(manifest)
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
    build_variables, build_inputs = _build_model_surface(
        build_model_version, build_core_version, run=run
    )
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
    comparison = compare_input_surface(
        artifacts,
        variables,
        inputs,
        aliases,
        build_model_variables=build_variables,
        build_model_inputs=build_inputs,
    )
    if comparison["dropped_columns"]:
        raise RegionalInputSurfaceError(
            f"Columns policyengine-uk {build_model_version} defines and "
            f"{model_version} does not would be dropped, which refuses "
            f"acceptance: {comparison['dropped_columns']}."
        )
    return RegionalInputSurfaceEvidence(
        regional_manifest_uri=regional_manifest_uri,
        regional_manifest_sha256=manifest_sha256,
        model_package="policyengine-uk",
        model_version=model_version,
        build_model_version=build_model_version,
        build_core_version=build_core_version,
        artifacts=artifacts,
        model_variables=variables,
        model_inputs=inputs,
        build_model_variables=build_variables,
        build_model_inputs=build_inputs,
        input_aliases=aliases,
        dropped_columns=comparison["dropped_columns"],
        never_modelled_columns=comparison["never_modelled_columns"],
        defaulted_inputs=comparison["defaulted_inputs"],
        audited_by=audited_by,
        limitations=limitations,
    )
