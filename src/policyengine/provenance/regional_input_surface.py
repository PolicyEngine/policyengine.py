"""Audit regional H5 bytes against their build model and the exact target.

A local-area release keeps serving area runs after the national bundle moves
to a newer policyengine-uk or policyengine-us. The audit compares the columns
actually stored in
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
The build model is read in a throwaway ``uv run`` environment, from PyPI as it
was when the release was built, so the audit needs ``uv`` and PyPI. Input
moves are read from the installed target model's constructor, so an alias
cannot make a supplied input look defaulted. Certification reads both models
again (``verify_model_surfaces``); only the stored columns rest on the
auditor's word, bound to each H5's SHA-256. No household values are included
in the resulting audit.

The two countries differ in three ways. A UK file stores entity tables, read
with PyTables. A US file is in either layout .py's US loader reads:
single-year entity tables (the Microcosm ACS-local release's, with
``_time_period`` naming the year), or PolicyEngine core's variable/period
layout (an H5 group per variable, an array per period), read with h5py. A UK
input alias
is policyengine-uk's ``move_values`` from one variable it defines to another;
a US alias is .py's rename of a stored input policyengine-us no longer defines
onto its live input (``LEGACY_INPUT_RENAMES``). And each country's build model
is read with its own package.

policyengine-uk 2.147.2 silently skips unknown columns in both dataset loaders;
the audit must detect that loss before certification. See the ``continue``
branches in ``build_from_dataset`` and ``build_from_multi_year_dataset``:
https://github.com/PolicyEngine/policyengine-uk/blob/fe0b99a36bd309a722b19937345e34290cb6dd73/policyengine_uk/simulation.py#L1113-L1127
https://github.com/PolicyEngine/policyengine-uk/blob/fe0b99a36bd309a722b19937345e34290cb6dd73/policyengine_uk/simulation.py#L1186-L1196
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import re
import subprocess
import sys
import textwrap
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
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
#: The tables a US entity-table H5 stores, as .py's US loader reads them.
US_ENTITIES = ("person", "household", "tax_unit", "spm_unit", "family", "marital_unit")
#: The table naming the year a single-year entity-table H5 holds, by country.
UK_TIME_PERIOD_KEY = "/time_period"
US_TIME_PERIOD_KEY = "/_time_period"
#: The country models an audit reads, by package: the module each imports as.
MODEL_MODULES = {
    "policyengine-uk": "policyengine_uk",
    "policyengine-us": "policyengine_us",
}
#: .py's register of renamed US inputs, the US input aliases.
US_LEGACY_INPUTS_MODULE = "policyengine.tax_benefit_models.us.legacy_inputs"
#: A US file in PolicyEngine core's variable/period layout has this group.
US_CORE_LAYOUT_MARKER = "person_id"
#: The interpreter of the throwaway environment that reads the build model.
BUILD_MODEL_PYTHON = "3.13"
#: The only index that environment resolves from.
BUILD_MODEL_INDEX = "https://pypi.org/simple"
#: uv settings that environment keeps: where uv caches and how it connects,
#: none of which changes what resolves. Every other ``UV_*`` setting (indexes,
#: constraints, overrides, the caller's project) and ``VIRTUAL_ENV`` are
#: removed.
BUILD_MODEL_KEPT_UV_SETTINGS = frozenset(
    {
        "UV_CACHE_DIR",
        "UV_CONCURRENT_DOWNLOADS",
        "UV_CONCURRENT_INSTALLS",
        "UV_HTTP_TIMEOUT",
        "UV_LINK_MODE",
        "UV_NATIVE_TLS",
        "UV_NO_PROGRESS",
        "UV_PYTHON_CACHE_DIR",
        "UV_PYTHON_INSTALL_DIR",
    }
)
#: Runs in the build model's environment: the model API ``_model_surface``
#: uses, and the package versions it actually imported.
_BUILD_MODEL_PROBE_TEMPLATE = """
import json
from importlib.metadata import version

import {module}

system = {module}.CountryTaxBenefitSystem()
print(json.dumps({{
    "model_version": version("{package}"),
    "core_version": version("policyengine-core"),
    "variables": sorted(system.variables),
    "inputs": sorted(
        name
        for name, variable in system.variables.items()
        if variable.is_input_variable()
    ),
}}))
"""


class RegionalInputSurfaceError(ValueError):
    """A complete, byte-bound regional surface cannot be established."""


def _model_module(model_package: str) -> str:
    """Return the module ``model_package`` imports as; refuse other packages."""
    try:
        return MODEL_MODULES[model_package]
    except KeyError as exc:
        raise RegionalInputSurfaceError(
            f"The audit reads policyengine-uk or policyengine-us, not {model_package}."
        ) from exc


def build_model_probe(model_package: str) -> str:
    """Return the probe that reads ``model_package``'s surface in its environment."""
    return _BUILD_MODEL_PROBE_TEMPLATE.format(
        module=_model_module(model_package), package=model_package
    )


#: The UK probe, kept under its earlier name.
BUILD_MODEL_PROBE = build_model_probe("policyengine-uk")


def readable(text: str) -> bool:
    """Whether ``text`` shows a reader anything.

    ``str.strip`` and a ``\\S`` pattern both accept text made only of
    invisible format characters, such as a zero-width space, so this needs
    one printable character that is not whitespace.
    """
    return any(char.isprintable() and not char.isspace() for char in text)


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
    model_package: str = "policyengine-uk",
) -> dict[str, list[str]]:
    """Recompute dropped, never-modelled and defaulted names per period.

    ``dropped_columns`` are stored columns the build model defines and the
    target model does not. ``never_modelled_columns`` are stored columns
    neither model defines. ``defaulted_inputs`` are target inputs a period
    does not supply that were not inputs of the build model. Inputs supplied
    by the target's unconditional ``move_values`` calls use the destination
    name after the move. Every artifact and period must pass: the union of
    supplied columns cannot hide a missing input in another period.

    An alias has its model's shape. A policyengine-uk move reads a variable
    the target defines; a policyengine-us rename reads a stored legacy input
    the target no longer defines. A stored alias source is read, so it is
    neither dropped nor never modelled.
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
    renames = _model_module(model_package) == "policyengine_us"
    for donor, target in aliases.items():
        if (
            (donor in variables if renames else donor not in variables)
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
        stored = set(artifact.columns)
        for supplied in periods:
            # A UK move always applies. .py applies a US rename only where the
            # live input is not stored: across the whole file in the
            # variable/period layout, and in the live input's entity table in
            # an entity-table file. The evidence keeps one column list per
            # file, so for entity tables this checks across all of them: a
            # legacy column stored in another entity's table counts as mapped.
            mapped = {
                donor
                for donor, target in aliases.items()
                if donor in supplied and not (renames and target in stored)
            }
            dropped.update((supplied & build_variables) - variables - mapped)
            never_modelled.update(supplied - build_variables - variables - mapped)
            effective = (supplied - mapped) | {aliases[donor] for donor in mapped}
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


def _us_input_aliases(variables: Any) -> dict[str, str]:
    """Return .py's renames of stored legacy inputs this policyengine-us needs.

    These are the ``LEGACY_INPUT_RENAMES`` entries whose live input the engine
    defines and whose legacy name it does not, as the US loaders apply them.
    """
    module = sys.modules.get(US_LEGACY_INPUTS_MODULE)
    if module is None:
        # Loaded from its file: importing it through its package would run
        # ``policyengine.tax_benefit_models.us``'s ``__init__``, which builds
        # .py's pinned US model and checks the installed bundle's certification.
        # The audit runs before the bundle certifies the target.
        path = (
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("tax_benefit_models", "us", "legacy_inputs.py")
        )
        spec = importlib.util.spec_from_file_location(
            "policyengine_regional_audit_us_legacy_inputs", path
        )
        if spec is None or spec.loader is None:
            raise RegionalInputSurfaceError(
                "Cannot read .py's register of renamed US inputs."
            )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module.pending_legacy_input_renames(variables)


def _model_surface(
    model_version: str, model_package: str = "policyengine-uk"
) -> tuple[list[str], list[str], dict[str, str]]:
    module_name = _model_module(model_package)
    try:
        installed = version(model_package)
    except PackageNotFoundError as exc:
        raise RegionalInputSurfaceError(
            f"Install the exact {model_package} target first."
        ) from exc
    if installed != model_version:
        raise RegionalInputSurfaceError(
            f"Installed {model_package} {installed} differs from requested {model_version}."
        )
    # Imported here, not at module level: importing this module must not load
    # the country model. The audit and certification's verify_model_surfaces
    # load it on purpose.
    model = importlib.import_module(module_name)

    system = model.CountryTaxBenefitSystem()
    variables = sorted(system.variables)
    inputs = sorted(
        name
        for name, variable in system.variables.items()
        if variable.is_input_variable()
    )
    if module_name == "policyengine_us":
        return variables, inputs, _us_input_aliases(system.variables)
    return variables, inputs, _input_aliases(model.Simulation)


def regional_build_versions(manifest: DataReleaseManifest) -> tuple[str, str, str]:
    """Return the regional release's build model package, its version and core.

    These are the audit baseline. A release that records neither, or records
    a package the audit does not read, refuses: there is no model to tell a
    dropped column from one no model ever defined.
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
    if model.name not in MODEL_MODULES or core.name != "policyengine-core":
        raise RegionalInputSurfaceError(
            f"The regional release was built with {model.name} and {core.name}, "
            "not policyengine-uk or policyengine-us, and policyengine-core."
        )
    for package in (model, core):
        try:
            Version(package.version)
        except InvalidVersion as exc:
            raise RegionalInputSurfaceError(
                f"The regional manifest's {package.name} build version "
                f"{package.version!r} is not a version."
            ) from exc
    return model.name, model.version, core.version


def regional_build_cutoff(manifest: DataReleaseManifest) -> str:
    """Return when the regional release was built, as a UTC ``--exclude-newer``.

    The build model is read with the packages PyPI had then, so its other
    dependencies resolve as they did at the build however they move on.
    Rounded up to the second. A manifest that records no ``build.built_at``
    refuses, as one without build versions does: the read would not be
    reproducible.
    """
    built_at = manifest.build.built_at if manifest.build is not None else None
    if built_at is None:
        raise RegionalInputSurfaceError(
            "The regional manifest records no build.built_at, so the build model "
            "cannot be read as of its build."
        )
    try:
        moment = datetime.fromisoformat(built_at)
    except ValueError as exc:
        raise RegionalInputSurfaceError(
            f"The regional manifest's build.built_at {built_at!r} is not a timestamp."
        ) from exc
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    moment = moment.astimezone(UTC)
    if moment.microsecond:
        moment = moment.replace(microsecond=0) + timedelta(seconds=1)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_model_surface(
    model_version: str,
    core_version: str,
    run: Callable[..., Any] | None = None,
    exclude_newer: str | None = None,
    model_package: str = "policyengine-uk",
) -> tuple[list[str], list[str]]:
    """Read the build model's variables and inputs in a throwaway environment.

    ``uv run --isolated --no-project --no-config`` installs exactly the two
    pins from PyPI into a fresh environment, with packages uploaded before
    ``exclude_newer`` when it is given, and without the caller's uv settings,
    project or environment. Without ``--isolated``, uv would reuse an
    environment that already meets both pins, such as a ``.venv`` in the
    working directory, and neither the index nor the cutoff would apply. The
    probe reports the versions it imported, and any other resolution refuses.
    """
    run = run if run is not None else subprocess.run
    probe = build_model_probe(model_package)
    label = f"{model_package} {model_version} with policyengine-core {core_version}"
    command = [
        "uv",
        "run",
        "--isolated",
        "--no-project",
        "--no-config",
        "--default-index",
        BUILD_MODEL_INDEX,
        *(["--exclude-newer", exclude_newer] if exclude_newer else []),
        "--python",
        BUILD_MODEL_PYTHON,
        "--with",
        f"{model_package}=={model_version}",
        "--with",
        f"policyengine-core=={core_version}",
        "python",
        "-I",
        "-c",
        probe,
    ]
    env = {
        key: value
        for key, value in os.environ.items()
        if key != "VIRTUAL_ENV"
        and (not key.startswith("UV_") or key in BUILD_MODEL_KEPT_UV_SETTINGS)
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
            f"The build-model probe resolved {model_package} {resolved[0]} with "
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


def _surface_difference(claimed: list[str], actual: list[str]) -> str:
    extra = sorted(set(claimed) - set(actual))
    missing = sorted(set(actual) - set(claimed))
    shown = [f"+{name}" for name in extra[:5]] + [f"-{name}" for name in missing[:5]]
    return ", ".join(shown) or "order or duplicates"


def verify_model_surfaces(
    evidence: RegionalInputSurfaceEvidence,
    regional_manifest: DataReleaseManifest,
    *,
    run: Callable[..., Any] | None = None,
) -> None:
    """Refuse evidence whose model surfaces are not the models' own.

    Certification calls this, so editing the evidence cannot hide a dropped
    column. The target model must be installed at ``evidence.model_version``:
    its variables, inputs and input aliases are read in process, as the audit
    reads them. The build model is read again in a throwaway ``uv run``
    environment, as the audit reads it. The stored columns cannot be re-read
    without the H5: the auditor attests them, and the evidence binds them to
    each H5's SHA-256.
    """
    package = evidence.model_package
    variables, inputs, aliases = _model_surface(
        evidence.model_version, model_package=package
    )
    target = f"{package} {evidence.model_version}"
    for field, claimed, actual in (
        ("model_variables", evidence.model_variables, variables),
        ("model_inputs", evidence.model_inputs, inputs),
    ):
        if claimed != actual:
            raise RegionalInputSurfaceError(
                f"The evidence's {field} are not {target}'s "
                f"({_surface_difference(claimed, actual)})."
            )
    if (evidence.input_aliases or {}) != aliases:
        raise RegionalInputSurfaceError(
            f"The evidence's input_aliases are not {target}'s."
        )
    build_variables, build_inputs = _build_model_surface(
        evidence.build_model_version,
        evidence.build_core_version,
        run=run,
        exclude_newer=regional_build_cutoff(regional_manifest),
        model_package=package,
    )
    build = (
        f"{package} {evidence.build_model_version} with policyengine-core "
        f"{evidence.build_core_version}"
    )
    for field, claimed, actual in (
        ("build_model_variables", evidence.build_model_variables, build_variables),
        ("build_model_inputs", evidence.build_model_inputs, build_inputs),
    ):
        if claimed != actual:
            raise RegionalInputSurfaceError(
                f"The evidence's {field} are not {build}'s "
                f"({_surface_difference(claimed, actual)})."
            )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hdf_columns(
    path: Path,
    entities: tuple[str, ...] = UK_ENTITIES,
    time_period_key: str = UK_TIME_PERIOD_KEY,
    country: str = "UK",
    multi_year: bool = True,
) -> dict[str, list[str]]:
    """Return each period's stored columns in an entity-table H5.

    A single-year file stores one table per entity and names its year in
    ``time_period_key``; a multi-year file stores ``<entity>/<year>`` tables,
    which only countries whose loaders read them accept (``multi_year``).
    Reads column names only, never a row. Other keys are producer metadata.
    """
    import pandas as pd

    try:
        with pd.HDFStore(path, mode="r") as store:
            keys = set(store.keys())
            flat = {f"/{entity}" for entity in entities} & keys
            nested = {
                key
                for key in keys
                if any(key.startswith(f"/{entity}/") for entity in entities)
            }
            if nested and not multi_year:
                raise RegionalInputSurfaceError(
                    f"{path.name} stores {country} entity tables by year; .py's "
                    f"{country} loaders read single-year files, one table per entity."
                )
            if flat and nested:
                raise RegionalInputSurfaceError(
                    "H5 mixes single-year and multi-year entity keys."
                )
            entity_keys: dict[str, dict[str, str]] = {}
            if flat:
                if time_period_key not in keys:
                    raise RegionalInputSurfaceError(
                        f"Single-year H5 requires {time_period_key}."
                    )
                metadata = store.select(time_period_key)
                values = metadata.to_numpy().ravel().tolist()
                if len(values) != 1 or not re.fullmatch(r"[0-9]{4}", str(values[0])):
                    raise RegionalInputSurfaceError(
                        f"H5 {time_period_key} must name one year."
                    )
                entity_keys[str(values[0])] = {
                    entity: f"/{entity}" for entity in entities if f"/{entity}" in flat
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
                raise RegionalInputSurfaceError(f"H5 has no {country} entity periods.")
            columns_by_period = {}
            for period, period_keys in sorted(entity_keys.items()):
                missing = set(entities) - set(period_keys)
                if missing:
                    raise RegionalInputSurfaceError(
                        f"H5 period {period} is missing {country} entity tables: "
                        f"{sorted(missing)}."
                    )
                columns: set[str] = set()
                for entity in entities:
                    # This obtains the same column metadata for fixed and table
                    # stores without selecting household or person rows.
                    frame = store.select(period_keys[entity], start=0, stop=0)
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


def _us_core_h5_columns(path: Path) -> dict[str, list[str]]:
    """Return each year's stored variables in a US core variable/period H5.

    Reads group and period names only, never an array. A top-level dataset is
    file metadata (such as .py's renames record), not a variable.
    """
    import h5py  # noqa: PLC0415

    try:
        with h5py.File(path, "r") as file:
            if not isinstance(file.get(US_CORE_LAYOUT_MARKER), h5py.Group):
                raise RegionalInputSurfaceError(
                    f"{path.name} is not in PolicyEngine core's variable/period "
                    f"layout: it has no {US_CORE_LAYOUT_MARKER} group."
                )
            columns_by_period: dict[str, set[str]] = {}
            for name, node in file.items():
                if not isinstance(node, h5py.Group):
                    continue
                periods = list(node.keys())
                if not periods:
                    raise RegionalInputSurfaceError(
                        f"{path.name} stores {name!r} for no period."
                    )
                for period in periods:
                    if not re.fullmatch(r"[0-9]{4}", period):
                        raise RegionalInputSurfaceError(
                            f"{path.name} stores {name!r} for period {period!r}; "
                            "the audit reads year periods only."
                        )
                    columns_by_period.setdefault(period, set()).add(name)
            return {
                period: sorted(_names(sorted(names), f"{period} columns"))
                for period, names in sorted(columns_by_period.items())
            }
    except RegionalInputSurfaceError:
        raise
    except (OSError, KeyError, ValueError, ImportError) as exc:
        raise RegionalInputSurfaceError(
            f"Cannot read H5 variable metadata from {path.name}."
        ) from exc


def _us_layout(path: Path) -> str:
    """Return which of .py's two US layouts a file uses: ``core`` or ``entity``."""
    import h5py  # noqa: PLC0415

    try:
        with h5py.File(path, "r") as file:
            if isinstance(file.get(US_CORE_LAYOUT_MARKER), h5py.Group):
                return "core"
            if any(entity in file for entity in US_ENTITIES):
                return "entity"
    except OSError as exc:
        raise RegionalInputSurfaceError(f"Cannot read {path.name} as H5.") from exc
    raise RegionalInputSurfaceError(
        f"{path.name} is in neither US layout .py loads: it has no "
        f"{US_CORE_LAYOUT_MARKER} group (PolicyEngine core's variable/period "
        f"layout) and no entity tables ({', '.join(US_ENTITIES)})."
    )


def _stored_columns(path: Path, model_package: str) -> dict[str, list[str]]:
    """Read a regional H5's stored columns in its country's layout."""
    if _model_module(model_package) != "policyengine_us":
        return _hdf_columns(path)
    if _us_layout(path) == "core":
        return _us_core_h5_columns(path)
    return _hdf_columns(path, US_ENTITIES, US_TIME_PERIOD_KEY, "US", multi_year=False)


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
    before and after metadata inspection. The installed target must be
    ``model_version``. The country model is the one the manifest's build
    model names, policyengine-uk or policyengine-us. The build model and core
    named by the manifest are
    read in a throwaway ``uv run`` environment through ``run``
    (``subprocess.run`` by default), resolving as of the manifest's
    ``build.built_at``. Dropped columns refuse. This reads no unit values for
    output.
    """
    # Imported lazily: the certification gate reuses compare_input_surface.
    from policyengine.provenance.certification import fetch_release_manifest

    if (
        not readable(audited_by)
        or not limitations
        or not all(readable(item) for item in limitations)
    ):
        raise RegionalInputSurfaceError(
            "An auditor and limitations a reader can see are required."
        )
    manifest, manifest_sha256, parts = fetch_release_manifest(
        regional_manifest_uri, token=token
    )
    model_package, build_model_version, build_core_version = regional_build_versions(
        manifest
    )
    build_cutoff = regional_build_cutoff(manifest)
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
    variables, inputs, aliases = _model_surface(
        model_version, model_package=model_package
    )
    build_variables, build_inputs = _build_model_surface(
        build_model_version,
        build_core_version,
        run=run,
        exclude_newer=build_cutoff,
        model_package=model_package,
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
        periods = _stored_columns(path, model_package)
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
        model_package=model_package,
    )
    if comparison["dropped_columns"]:
        raise RegionalInputSurfaceError(
            f"Columns {model_package} {build_model_version} defines and "
            f"{model_version} does not would be dropped, which refuses "
            f"acceptance: {comparison['dropped_columns']}."
        )
    return RegionalInputSurfaceEvidence(
        schema_version=2,
        regional_manifest_uri=regional_manifest_uri,
        regional_manifest_sha256=manifest_sha256,
        model_package=model_package,
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
