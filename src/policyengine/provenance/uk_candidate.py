"""Mandatory local qualification gates for a UK model/data candidate.

Each gate returns a :class:`~policyengine.provenance.qualification.GateResult`
and an evidence dict whose ``content_sha256`` the result records. No gate has
a skip path: a gate whose harness is missing reports ``unavailable`` (the
candidate is incomplete), a gate that crashes reports ``error`` (rejected),
and a failed check reports ``fail`` (rejected). The replay gate is evaluated
separately (:func:`policyengine.provenance.qualification.evaluate_replay_receipt`).

I/O is injected (metadata readers, HTTP getters, importers, year projectors)
so every gate is testable offline. :func:`run_candidate_gates` wires the real
implementations for the qualification workflow.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import io
import json
import math
import re
import sys
import traceback
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from policyengine.provenance.manifest import DataReleaseManifest, _specifier_matches
from policyengine.provenance.qualification import (
    CandidatePair,
    GateResult,
    QualificationHarness,
    QualificationReceipt,
)
from policyengine.provenance.receipt import content_sha256
from policyengine.provenance.wheels import (
    verify_installed_against_wheel,
)
from policyengine.utils.hashing import sha256_file

Evidence = dict[str, Any]
GateOutcome = tuple[GateResult, Evidence]

UK_SINGLE_YEAR_KEYS = ("time_period", "person", "benunit", "household")
ENTITY_TABLES = ("person", "benunit", "household")


def _json_safe(value: Any) -> Any:
    """Evidence as strict JSON: NumPy scalars become the Python numbers they
    hold (never their text), and non-finite numbers become their names."""

    numpy = sys.modules.get("numpy")
    if numpy is not None and isinstance(
        value, numpy.bool_ | numpy.integer | numpy.floating
    ):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return (
            "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
        )
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    return value


def evidence_sha256(evidence: Any) -> str:
    """Digest of evidence that may contain non-finite numbers."""

    return content_sha256(_json_safe(evidence))


def _result(
    gate_id: str,
    status: str,
    summary: str,
    evidence: Evidence,
    details: Optional[Mapping[str, Any]] = None,
) -> GateOutcome:
    result = GateResult(
        gate_id=gate_id,
        status=status,  # type: ignore[arg-type]
        summary=summary,
        evidence_sha256=evidence_sha256(evidence),
        details=_json_safe(dict(details or {})),
    )
    return result, _json_safe(evidence)


# --- 1. Installed versions ---------------------------------------------------


def installed_versions(
    pair: CandidatePair,
    harness: QualificationHarness,
    *,
    metadata: Any = importlib_metadata,
) -> GateOutcome:
    """Installed wrapper, model and core equal the candidate; requirements hold."""

    expected = {
        "policyengine": harness.policyengine_version,
        pair.model.name: pair.model.version,
        pair.core.name: pair.core.version,
    }
    installed: dict[str, Optional[str]] = {}
    problems: list[str] = []
    for name, version in expected.items():
        try:
            installed[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed[name] = None
            problems.append(f"{name} is not installed")
            continue
        if installed[name] != version:
            problems.append(f"{name} {installed[name]} is installed, not {version}")

    unmet: list[str] = []
    for name in expected:
        if installed.get(name) is None:
            continue
        for line in metadata.requires(name) or []:
            requirement = Requirement(line)
            if requirement.marker is not None and not requirement.marker.evaluate(
                {"extra": ""}
            ):
                continue
            try:
                found = metadata.version(requirement.name)
            except metadata.PackageNotFoundError:
                unmet.append(f"{name} needs {requirement}, which is not installed")
                continue
            if requirement.specifier and not requirement.specifier.contains(
                found, prereleases=True
            ):
                unmet.append(f"{name} needs {requirement}; {found} is installed")
    problems.extend(unmet)
    evidence = {
        "expected": expected,
        "installed": installed,
        "unmet_requirements": unmet,
    }
    if problems:
        return _result("installed_versions", "fail", "; ".join(problems), evidence)
    return _result(
        "installed_versions",
        "pass",
        f"policyengine {harness.policyengine_version}, {pair.model.name} {pair.model.version} and {pair.core.name} {pair.core.version} are installed and "
        "their requirements hold.",
        evidence,
    )


# --- 2. Wheel hashes -----------------------------------------------------------


def wheel_hashes(
    pair: CandidatePair,
    *,
    wheel_paths: Mapping[str, Path],
    pypi_digests: Mapping[str, str],
    metadata: Any = importlib_metadata,
) -> GateOutcome:
    """Downloaded wheels match PyPI and the pin; installed files match the wheels."""

    evidence: Evidence = {}
    problems: list[str] = []
    for package in (pair.model, pair.core):
        path = wheel_paths.get(package.name)
        if path is None or not Path(path).is_file():
            problems.append(f"no downloaded wheel for {package.name}")
            continue
        actual = sha256_file(path)
        if actual != package.wheel_sha256:
            problems.append(
                f"{package.name} wheel is {actual}, pinned {package.wheel_sha256}"
            )
        if pypi_digests.get(package.name) != package.wheel_sha256:
            problems.append(f"PyPI publishes a different {package.name} wheel digest")
        verification = verify_installed_against_wheel(
            package.name, Path(path), metadata=metadata
        )
        evidence[package.name] = verification
        problems.extend(f"{package.name} {item}" for item in verification["problems"])
    if problems:
        return _result("wheel_hashes", "fail", "; ".join(problems[:10]), evidence)
    counts = ", ".join(
        f"{name}: {item['archive_members_verified']} wheel members, "
        f"{item['files_verified']} installed files"
        for name, item in evidence.items()
    )
    return _result(
        "wheel_hashes",
        "pass",
        f"The pinned PyPI wheels match their RECORDs and the installed files ({counts}).",
        evidence,
    )


def receipt_wheel_paths(
    pair: CandidatePair, wheel_paths: Mapping[str, Path]
) -> dict[str, Path]:
    """``wheel_paths`` for ``build_execution_receipt``, which re-verifies them."""

    return {
        package.name: Path(wheel_paths[package.name])
        for package in (pair.model, pair.core)
        if package.name in wheel_paths
    }


# --- 3. Core compatibility -----------------------------------------------------


def core_compatibility(
    pair: CandidatePair,
    release_manifest: DataReleaseManifest,
    *,
    model_requires_core: str,
) -> GateOutcome:
    """The core satisfies the model; publisher claims are recorded, not required."""

    problems: list[str] = []
    if not SpecifierSet(model_requires_core).contains(
        pair.core.version, prereleases=True
    ):
        problems.append(
            f"{pair.model.name} {pair.model.version} requires policyengine-core"
            f"{model_requires_core}; the candidate core is {pair.core.version}"
        )
    build = release_manifest.build
    built_with = build.built_with_model_package if build is not None else None
    if built_with is not None and built_with.name != pair.model.name:
        problems.append(
            f"the data was built with {built_with.name}, not {pair.model.name}"
        )
    model_claims = [
        package.specifier
        for package in release_manifest.compatible_model_packages
        if package.name == pair.model.name
    ]
    core_claims = [
        package.specifier
        for package in release_manifest.compatible_core_packages
        if package.name == pair.core.name
    ]
    evidence = {
        "model_requires_core": model_requires_core,
        "built_with_model_version": built_with.version if built_with else None,
        "built_with_core_version": (
            build.built_with_core_package.version
            if build is not None and build.built_with_core_package is not None
            else None
        ),
        "publisher_model_claims": model_claims,
        "publisher_core_claims": core_claims,
        "publisher_claim_covers_model": any(
            _specifier_matches(pair.model.version, item) for item in model_claims
        ),
        "publisher_claim_covers_core": any(
            _specifier_matches(pair.core.version, item) for item in core_claims
        ),
    }
    if problems:
        return _result("core_compatibility", "fail", "; ".join(problems), evidence)
    coverage = (
        "the publisher's claims cover both"
        if evidence["publisher_claim_covers_model"]
        and evidence["publisher_claim_covers_core"]
        else "certification will record an exact qualified pair, since the publisher's claims do not cover both"
    )
    return _result(
        "core_compatibility",
        "pass",
        f"policyengine-core {pair.core.version} satisfies {pair.model.name}{model_requires_core}; {coverage}.",
        evidence,
        details={
            "publisher_claim_covers_model": evidence["publisher_claim_covers_model"],
            "publisher_claim_covers_core": evidence["publisher_claim_covers_core"],
        },
    )


# --- 4. Data access ------------------------------------------------------------


def _hf_url(repo_id: str, repo_type: str, revision: str, path: str) -> str:
    prefix = "datasets/" if repo_type == "dataset" else ""
    return f"https://huggingface.co/{prefix}{repo_id}/resolve/{revision}/{path}"


def data_access(
    pair: CandidatePair,
    *,
    get: Callable[..., Any],
    head: Callable[..., Any],
    token: Optional[str],
) -> tuple[GateResult, Evidence, Optional[DataReleaseManifest]]:
    """Authenticated access to the exact manifest and every artifact."""

    data = pair.data
    evidence: Evidence = {"artifacts": {}}
    if not token:
        result, evidence = _result(
            "data_access",
            "fail",
            "No Hugging Face token is configured; the UK data is private.",
            evidence,
        )
        return result, evidence, None
    headers = {"Authorization": f"Bearer {token}"}
    manifest_url = _hf_url(
        data.repo_id,
        data.repo_type,
        data.release_manifest_revision,
        data.release_manifest_path,
    )
    response = get(manifest_url, headers=headers, timeout=60)
    evidence["manifest_status"] = response.status_code
    if response.status_code != 200:
        result, evidence = _result(
            "data_access",
            "fail",
            f"The release manifest returned HTTP {response.status_code}.",
            evidence,
        )
        return result, evidence, None
    manifest_sha256 = hashlib.sha256(response.content).hexdigest()
    evidence["manifest_sha256"] = manifest_sha256
    problems = []
    if manifest_sha256 != data.release_manifest_sha256:
        problems.append("the release manifest bytes differ from the candidate's")
    manifest = DataReleaseManifest.model_validate_json(response.content)
    for name, artifact in sorted(manifest.artifacts.items()):
        url = _hf_url(
            artifact.repo_id,
            artifact.repo_type or data.repo_type,
            artifact.revision,
            artifact.path,
        )
        status = head(
            url, headers=headers, timeout=60, allow_redirects=True
        ).status_code
        evidence["artifacts"][name] = status
        if status != 200:
            problems.append(f"{name} returned HTTP {status}")
    dataset_url = _hf_url(
        data.repo_id, data.repo_type, data.dataset_revision, data.dataset_path
    )
    anonymous = head(dataset_url, timeout=60, allow_redirects=True).status_code
    evidence["anonymous_dataset_status"] = anonymous
    if anonymous == 200:
        problems.append(
            "the dataset is readable without credentials, so the authenticated path was not tested"
        )
    if problems:
        result, evidence = _result("data_access", "fail", "; ".join(problems), evidence)
        return result, evidence, manifest
    result, evidence = _result(
        "data_access",
        "pass",
        f"Read the release manifest and {len(manifest.artifacts)} artifacts with the "
        f"configured credential; anonymous access returned HTTP {anonymous}.",
        evidence,
    )
    return result, evidence, manifest


# --- 5. Dataset bytes ----------------------------------------------------------


def h5_keys(path: Path) -> list[str]:
    import h5py

    with h5py.File(path, "r") as stream:
        return sorted(stream.keys())


def dataset_bytes(pair: CandidatePair, dataset_path: Path) -> GateOutcome:
    """The simulated file is the candidate's bytes and has the UK layout."""

    data = pair.data
    actual = sha256_file(dataset_path)
    size = dataset_path.stat().st_size
    keys = h5_keys(dataset_path)
    evidence = {"sha256": actual, "size_bytes": size, "h5_keys": keys}
    problems = []
    if actual != data.dataset_sha256:
        problems.append(f"sha256 {actual}, expected {data.dataset_sha256}")
    if size != data.size_bytes:
        problems.append(f"{size} bytes, expected {data.size_bytes}")
    missing_keys = [key for key in UK_SINGLE_YEAR_KEYS if key not in keys]
    if missing_keys:
        problems.append(f"missing H5 keys {missing_keys}")
    if problems:
        return _result("dataset_bytes", "fail", "; ".join(problems), evidence)
    return _result(
        "dataset_bytes",
        "pass",
        f"{data.dataset} is the pinned {size:,} bytes with the UK single-year layout.",
        evidence,
    )


# --- 6. Supported years --------------------------------------------------------


def data_year(dataset_path: Path) -> int:
    import pandas as pd

    with pd.HDFStore(dataset_path, mode="r") as store:
        return int(str(store["time_period"].iloc[0])[:4])


def projected_years_from_model(dataset_path: Path) -> list[int]:
    """The years policyengine-uk projects a single-year dataset to.

    Builds the multi-year dataset exactly as ``policyengine_uk.Simulation``
    does for a single-year file (``extend_single_year_dataset`` with the
    system's parameters), without running any formula.
    """

    from policyengine_uk.data.dataset_schema import UKSingleYearDataset
    from policyengine_uk.data.economic_assumptions import extend_single_year_dataset
    from policyengine_uk.system import system

    multi_year = extend_single_year_dataset(
        UKSingleYearDataset(str(dataset_path)), system.parameters
    )
    years = getattr(multi_year, "years", None)
    if years is None:
        years = list(multi_year.datasets)
    return sorted(int(year) for year in years)


def supported_years(
    pair: CandidatePair,
    dataset_path: Path,
    *,
    required_years: Sequence[int],
    budget_horizon_years: Sequence[int],
    previous_supported_years: Optional[Sequence[int]],
    projected_years: Callable[[Path], list[int]] = projected_years_from_model,
) -> GateOutcome:
    """Required years are inside the data's projection; support never shrinks.

    Support comes from the data and the model's projection, never from a
    calculation succeeding: policyengine-core fills years outside the
    projection (carrying or uprating the latest inputs), so a result there
    is not evidence of support.
    """

    first = data_year(dataset_path)
    years = projected_years(dataset_path)
    supported = sorted(year for year in years if year >= first)
    missing_required = sorted(set(required_years) - set(supported))
    lost = sorted(set(previous_supported_years or []) - set(supported))
    outside_horizon = sorted(set(budget_horizon_years) - set(supported))
    evidence = {
        "data_year": first,
        "supported_years": supported,
        "required_years": sorted(required_years),
        "budget_horizon_years": sorted(budget_horizon_years),
        "previous_supported_years": sorted(previous_supported_years or []),
        "lost_years": lost,
        "outside_projection": outside_horizon,
    }
    details = {"supported_years": supported, "outside_projection": outside_horizon}
    if not supported:
        return _result(
            "supported_years",
            "fail",
            f"The dataset supports no year: its data year is {first} and the model "
            f"projects only to {max(years) if years else 'nothing'}.",
            evidence,
            details,
        )
    if missing_required or lost:
        parts = []
        if missing_required:
            parts.append(
                f"required years {missing_required} are outside the projection"
            )
        if lost:
            parts.append(f"years {lost} were supported by the previous certificate")
        return _result("supported_years", "fail", "; ".join(parts), evidence, details)
    if outside_horizon:
        return _result(
            "supported_years",
            "needs_review",
            f"Budget horizon years {outside_horizon} are outside the dataset's projection "
            f"({supported[0]}–{supported[-1]}); results there are provisional.",
            evidence,
            details,
        )
    return _result(
        "supported_years",
        "pass",
        f"Supports {supported[0]}–{supported[-1]}, covering the required and horizon years.",
        evidence,
        details,
    )


# --- 7. Budget inputs ----------------------------------------------------------


def dataset_columns(dataset_path: Path) -> dict[str, Any]:
    """``{entity: DataFrame}`` for the UK entity tables."""

    import pandas as pd

    with pd.HDFStore(dataset_path, mode="r") as store:
        return {
            entity: store[entity] for entity in ENTITY_TABLES if f"/{entity}" in store
        }


def _degenerate(series: Any) -> bool:
    values = series.dropna()
    if len(values) == 0 or values.nunique() <= 1:
        return True
    if values.dtype.kind in "biuf":
        return bool((values.astype(float) == 0).all())
    return False


def budget_inputs(
    pair: CandidatePair,
    dataset_path: Path,
    *,
    model_input_variables: Iterable[str],
    critical_inputs: Sequence[str],
    accepted_gaps: Mapping[str, str],
    previous_missing_inputs: Optional[Sequence[str]],
    previous_unusable_critical: Optional[Sequence[str]],
    model_variables: Optional[Iterable[str]] = None,
    previous_input_status: Optional[Mapping[str, Mapping[str, bool]]] = None,
    previous_ever_usable_inputs: Optional[Sequence[str]] = None,
    tables: Optional[Mapping[str, Any]] = None,
) -> GateOutcome:
    """Critical inputs are present and usable; no input goes newly missing."""

    tables = dict(tables) if tables is not None else dataset_columns(dataset_path)
    columns: dict[str, str] = {}
    for entity, table in tables.items():
        for column in table.columns:
            columns.setdefault(column, entity)
    inputs = set(model_input_variables)
    model_names = inputs | set(model_variables or [])
    missing = sorted(inputs - set(columns))
    newly_missing = (
        sorted(set(missing) - set(previous_missing_inputs))
        if previous_missing_inputs is not None
        else []
    )
    unusable = []
    for name in critical_inputs:
        if name not in columns:
            unusable.append((name, "missing"))
        elif _degenerate(tables[columns[name]][name]):
            unusable.append((name, "degenerate"))
    previous_bad = set(previous_unusable_critical or [])
    regressions = [(n, why) for n, why in unusable if n not in previous_bad]
    standing = [(n, why) for n, why in unusable if n in previous_bad]
    unaccepted_standing = [(n, why) for n, why in standing if n not in accepted_gaps]
    input_status = {
        name: {
            "in_model": name in model_names,
            "is_input": name in inputs,
            "in_data": name in columns,
            "usable": name in model_names
            and name in columns
            and not _degenerate(tables[columns[name]][name]),
        }
        for name in sorted(model_names | set(columns))
    }
    # Keep the complete certified history even when an intermediate model
    # removes a variable or turns it into a formula. Direct-predecessor
    # coverage alone must never reactivate an expired exception.
    previous_ever_usable = set(previous_ever_usable_inputs or []) | {
        name
        for name, status in (previous_input_status or {}).items()
        if status.get("usable") is True
    }
    ever_usable = previous_ever_usable | {
        name for name, status in input_status.items() if status["usable"]
    }
    if previous_ever_usable_inputs is not None:
        lineage_basis = "carried from direct predecessor"
    elif previous_input_status is not None:
        lineage_basis = "seeded from direct predecessor"
    else:
        lineage_basis = "candidate inputs"
    evidence = {
        "pair_id": pair.pair_id,
        "model_input_variables": len(inputs),
        "model_variables": len(model_names),
        "dataset_columns": len(columns),
        "missing_inputs": missing,
        "newly_missing_inputs": newly_missing,
        "unusable_critical": [list(item) for item in unusable],
        "accepted_gaps": dict(accepted_gaps),
        "input_status": input_status,
        "previous_input_status": dict(previous_input_status or {}),
        "previous_ever_usable_inputs": sorted(previous_ever_usable),
        "ever_usable_inputs": sorted(ever_usable),
        "ever_usable_inputs_basis": lineage_basis,
    }
    details = {
        "missing_inputs": len(missing),
        "newly_missing_inputs": newly_missing,
        "unusable_critical": [name for name, _ in unusable],
        # This immutable receipt marker distinguishes legacy evidence from a
        # damaged modern cache, which must never reset the comparison chain.
        "ever_usable_inputs": sorted(ever_usable),
    }
    if regressions:
        return _result(
            "budget_inputs",
            "fail",
            "Budget-critical inputs became unusable: "
            + ", ".join(f"{name} ({why})" for name, why in regressions),
            evidence,
            details,
        )
    if unaccepted_standing or newly_missing:
        parts = []
        if newly_missing:
            parts.append(
                f"{len(newly_missing)} model inputs are newly missing from the data "
                f"({', '.join(newly_missing[:8])}{'…' if len(newly_missing) > 8 else ''})"
            )
        if unaccepted_standing:
            parts.append(
                "critical inputs unusable in both pairs: "
                + ", ".join(f"{name} ({why})" for name, why in unaccepted_standing)
            )
        return _result(
            "budget_inputs", "needs_review", "; ".join(parts), evidence, details
        )
    return _result(
        "budget_inputs",
        "pass",
        f"All {len(critical_inputs)} critical inputs are present and usable; "
        f"no model input is newly missing ({len(missing)} optional inputs absent, as before).",
        evidence,
        details,
    )


# --- 8. Reform contract --------------------------------------------------------


def _load_entrypoint(
    entrypoint: str, importer: Callable[[str], Any]
) -> tuple[Callable[..., Any], Any]:
    """The entrypoint's callable and the module that defines it."""

    module_name, _, attribute = entrypoint.partition(":")
    if not attribute:
        module_name, _, attribute = entrypoint.rpartition(".")
    module = importer(module_name)
    function: Callable[..., Any] = getattr(module, attribute)
    return function, module


def _contract_coverage(module: Any) -> Optional[dict[str, Any]]:
    """What a full contract run covers, as the runner's own module declares it.

    ``ROUTES`` (route ids), ``CASES`` (objects with an ``id`` and optional
    ``routes`` limiting where the case runs and ``checks`` describing each
    expected value), ``UNSUPPORTED_ROUTES`` and ``PROPERTIES`` (keyed by
    property id). ``None`` when the module does not declare the essentials.
    """

    try:
        routes = [str(route) for route in module.ROUTES]
        pairs = [
            (str(case.id), str(route))
            for case in module.CASES
            for route in (
                case.routes if getattr(case, "routes", None) is not None else routes
            )
        ]
        checks: list[tuple[str, str, Optional[str]]] = []
        assertions: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        unsupported = getattr(module, "UNSUPPORTED_ROUTES", {})
        country_routes = set(
            getattr(
                module,
                "COUNTRY_ROUTES",
                [route for route in routes if route.startswith("country.")],
            )
        )
        unsupported_checks = {}
        for case in module.CASES:
            for route in (
                case.routes if getattr(case, "routes", None) is not None else routes
            ):
                if route in unsupported:
                    key = (str(case.id), str(route), None)
                    checks.append(key)
                    unsupported_checks[key] = unsupported[route]
                elif getattr(case, "expect_error", None) is not None:
                    checks.append((str(case.id), str(route), "rejected"))
                else:
                    for index, check in enumerate(getattr(case, "checks", ())):
                        key = (
                            str(case.id),
                            str(route),
                            f"{check.target}:{check.name}:{check.year}",
                        )
                        checks.append(key)
                        assertion_id = f"{key[2]}:{index}"
                        assertions[(*key, assertion_id)] = {
                            "oracle": getattr(check, "oracle", None),
                            "pending": getattr(check, "pending", None),
                        }
                        # evaluate_case declares these per-check exemptions;
                        # route-wide exemptions above replace the entire case.
                        if check.target == "parameter" and route not in country_routes:
                            unsupported_checks[key] = (
                                "this route exposes outputs, not parameter values"
                            )
                        elif (
                            check.target == "baseline_equals"
                            and route == "wrapper.policy"
                        ):
                            unsupported_checks[key] = (
                                "the policy route's output dataset holds the reformed run only"
                            )

                    # The runner has no machine-readable isolation matrix.
                    # Derive its strongest coverage from _CountryRoute.run,
                    # _WrapperHouseholdRoute.run and _WrapperPolicyRoute.run:
                    # deduplicate requests; country baselines cover variable
                    # requests and after-runs cover parameters and variables;
                    # wrappers' after-runs cover exposed variables only.
                    # baseline_equals also requests its expected variable on
                    # country/household routes, but policy excludes that target.
                    # Rejected/error and whole-route unsupported cases emit no
                    # isolation rows. Every supported run also emits the shared
                    # module parameter check, required independently below.
                    requests = []
                    for check in getattr(case, "checks", ()):
                        if route not in country_routes and (
                            check.target == "parameter"
                            or (
                                route == "wrapper.policy"
                                and check.target == "baseline_equals"
                            )
                        ):
                            continue
                        kind = (
                            "parameter" if check.target == "parameter" else "variable"
                        )
                        requests.append((kind, str(check.name), check.year))
                        if check.target == "baseline_equals":
                            requests.append(
                                ("variable", str(check.expected), check.year)
                            )
                    for kind, name, year in dict.fromkeys(requests):
                        if route in country_routes and kind == "variable":
                            checks.append(
                                (
                                    str(case.id),
                                    str(route),
                                    f"baseline_isolation:{name}:{year}",
                                )
                            )
                        checks.append(
                            (
                                str(case.id),
                                str(route),
                                f"unreformed_after_reform:{name}:{year}",
                            )
                        )
        return {
            "routes": routes,
            "pairs": pairs,
            "properties": [str(name) for name in module.PROPERTIES],
            "checks": checks,
            "isolation_checks": {
                (case, route, check)
                for case, route, check in checks
                if isinstance(check, str)
                and check.startswith(
                    ("baseline_isolation:", "unreformed_after_reform:")
                )
            },
            "assertions": assertions,
            "pending_decisions": {
                str(decision) for decision in getattr(module, "PENDING_DECISIONS", ())
            },
            "unsupported_routes": unsupported,
            "unsupported_checks": unsupported_checks,
            "run_pairs": (
                [("module_parameters_unchanged", "all")]
                if any(route not in unsupported for route in routes)
                else []
            ),
            "population": getattr(module, "POPULATION_CHECK_ROUTES", None),
        }
    except AttributeError:
        return None


def _declared_population_checks(
    module_name: str, importer: Callable[[str], Any], routes: Sequence[str]
) -> list[tuple[str, str]]:
    """The runner's complete population check/route multiset."""

    module = importer(module_name.rsplit(".", 1)[0] + ".budget_reform_population")
    declared = getattr(module, "POPULATION_CHECK_ROUTES", None)
    if declared is not None:
        return [(str(check), str(route)) for check, route in declared]
    coverage = getattr(module, "population_check_routes", None)
    if callable(coverage):
        return [(str(check), str(route)) for check, route in coverage(routes)]
    # IDs alone cannot prove that every route ran. Retain their names in the
    # diagnostic, while refusing a runner with no per-route declaration.
    ids = getattr(module, "POPULATION_CHECKS", None) or re.findall(
        r"^``([a-z][a-z0-9_]+)``$", inspect.getdoc(module) or "", re.MULTILINE
    )
    raise AttributeError(
        "the population runner declares no population check routes"
        + (": " + ", ".join(str(check) for check in ids) if ids else "")
    )


def _reported_assertions(
    rows: Sequence[Mapping[str, Any]], coverage: Mapping[str, Any]
) -> tuple[dict[int, tuple[str, str, str, str]], list[str]]:
    """Resolve current assertion IDs and unambiguous historical oracle rows.

    Released reports predate assertion IDs. Their oracles distinguish checks
    with the same label. Whole-route exemptions have no values or oracles;
    their interchangeable rows are consumed in declaration order instead.
    """
    resolved = {}
    problems = []
    used: Counter[tuple[str, str, str, str]] = Counter()
    by_label: dict[tuple[str, str, str], list[tuple[str, str, str, str]]] = {}
    for key in coverage["assertions"]:
        by_label.setdefault(key[:3], []).append(key)
    for row in rows:
        label = (str(row.get("case_id")), str(row.get("route")), row.get("check"))
        matches = list(by_label.get(label, ()))
        if not matches:
            continue  # Isolation, run-level and rejected-case rows are separate.
        assertion_id = row.get("assertion_id")
        if assertion_id is not None:
            matches = [key for key in matches if key[3] == assertion_id]
            if row.get("oracle") is not None:
                matches = [
                    key
                    for key in matches
                    if coverage["assertions"][key]["oracle"] == row["oracle"]
                ]
        elif len(matches) > 1:
            if row.get("oracle") is not None:
                matches = [
                    key
                    for key in matches
                    if coverage["assertions"][key]["oracle"] == row["oracle"]
                ]
            elif (
                row.get("status") == "unsupported"
                and label in coverage["unsupported_checks"]
            ):
                matches = [key for key in matches if not used[key]][:1]
            else:
                matches = []
        if len(matches) != 1:
            problems.append(
                f"case {label[0]}@{label[1]}:{label[2]} has no unique declared assertion identity"
            )
            continue
        resolved[id(row)] = matches[0]
        used[matches[0]] += 1
    return resolved, problems


#: Report sections: the key that names each row, and what a row is called.
_CONTRACT_SECTIONS = (
    ("cases", "case_id", "case"),
    ("properties", "property_id", "property"),
    ("population", "check_id", "population check"),
)
_CONTRACT_STATUSES = ("pass", "fail", "error", "unsupported", "pending")
#: How the runner's run-level row names the shared parameter check. Contract
#: 1.0.0 continued "in ..."; 1.1.0 added node metadata and band order before
#: it, so only this stem is fixed.
RUN_LEVEL_CHECK_PREFIX = "every parameter's dated values and metadata"


def reform_contract(
    *,
    entrypoint: Optional[str],
    dataset_path: Optional[Path],
    seed: int,
    max_examples: int,
    expected_versions: Optional[Mapping[str, str]] = None,
    expected_dataset_sha256: Optional[str] = None,
    pending_decisions: Sequence[str] = (),
    importer: Callable[[str], Any] = importlib.import_module,
) -> GateOutcome:
    """Run the Budget reform contract (W1) on every route and gate on its report.

    ``fail`` when any case, sampled property or population check fails or
    errors. ``error`` when the report cannot be trusted as a full run of this
    candidate:
    - it does not cover every declared case check on each route, the runner's
      isolation checks and run-level shared-parameter check, every declared
      population check and every sampled property, or a property passed on
      fewer examples than requested;
    - a property is pending, a pending row names no authorized decision,
      or an unsupported case or population check has no runner-declared
      exemption with the same ``reason``;
    - a sampled property did not run;
    - population checks are missing although a dataset was given;
    - the report names other versions, another dataset, seed or sample size
      than requested;
    - its own ``holds`` or ``summary`` disagrees with its rows.
    """

    if not entrypoint:
        return _result(
            "reform_contract",
            "unavailable",
            "No reform contract runner is configured.",
            {},
        )
    try:
        runner, runner_module = _load_entrypoint(entrypoint, importer)
    except (ImportError, AttributeError) as exc:
        return _result(
            "reform_contract",
            "unavailable",
            f"The reform contract runner {entrypoint} is not importable: {exc}",
            {"entrypoint": entrypoint},
        )
    try:
        report = runner(
            routes=None,
            dataset_path=str(dataset_path) if dataset_path else None,
            seed=seed,
            max_examples=max_examples,
        )
    except Exception as exc:  # the candidate made the contract crash
        return _result(
            "reform_contract",
            "error",
            f"The reform contract raised {type(exc).__name__}: {exc}",
            {"entrypoint": entrypoint, "traceback": traceback.format_exc()},
        )
    report = json.loads(json.dumps(_json_safe(report), default=str))
    failures: list[str] = []
    malformed: list[str] = []
    pending: list[str] = []
    unsupported: list[str] = []
    counts = dict.fromkeys(_CONTRACT_STATUSES, 0)
    coverage = _contract_coverage(runner_module)
    reported_assertions = {}
    if coverage is not None:
        reported_assertions, assertion_problems = _reported_assertions(
            report.get("cases") or [], coverage
        )
        malformed.extend(assertion_problems)
    population_exemptions = {}
    population_module = None
    if dataset_path is not None:
        module_name = (
            entrypoint.partition(":")[0]
            if ":" in entrypoint
            else entrypoint.rpartition(".")[0]
        )
        try:
            population_module = importer(
                module_name.rsplit(".", 1)[0] + ".budget_reform_population"
            )
            population_exemptions = getattr(population_module, "UNSUPPORTED_CHECKS", {})
        except (ImportError, AttributeError):
            pass
    allowed_pending = set(pending_decisions) | (
        coverage["pending_decisions"] if coverage else set()
    )
    for section, key, noun in _CONTRACT_SECTIONS:
        for row in report.get(section) or []:
            status = row.get("status")
            label = f"{noun} {row.get(key)}" + (
                f"@{row['route']}" if row.get("route") else ""
            )
            if status in counts:
                counts[status] += 1
            if status in ("fail", "error"):
                failures.append(label)
            elif status == "pending":
                decision = row.get("decision_id")
                declared_decision = (
                    coverage["assertions"]
                    .get(reported_assertions.get(id(row)), {})
                    .get("pending")
                    if coverage and section == "cases"
                    else None
                )
                if section == "properties":
                    malformed.append(
                        f"{label} did not run: properties cannot be pending"
                    )
                elif section == "population":
                    malformed.append(
                        f"{label} is a mandatory assertion: population checks cannot be pending"
                    )
                elif not decision:
                    malformed.append(f"{label} is pending without a decision_id")
                elif section == "cases" and declared_decision is None:
                    malformed.append(
                        f"{label} is a mandatory assertion relabelled pending"
                    )
                elif section == "cases" and decision != declared_decision:
                    malformed.append(
                        f"{label} is pending for undeclared decision {decision}"
                    )
                elif decision != declared_decision and decision not in allowed_pending:
                    malformed.append(
                        f"{label} is pending for undeclared decision {decision}"
                    )
                pending.append(label)
            elif status == "unsupported":
                if section == "properties":
                    malformed.append(
                        f"{label} did not run: {row.get('reason') or 'no reason given'}"
                    )
                elif not row.get("reason"):
                    malformed.append(f"{label} is unsupported without a reason")
                elif section == "cases":
                    declared_reason = (
                        coverage["unsupported_checks"].get(
                            (
                                str(row.get("case_id")),
                                str(row.get("route")),
                                row.get("check"),
                            )
                        )
                        if coverage
                        else None
                    )
                    if declared_reason is None:
                        malformed.append(f"{label} is an undeclared unsupported check")
                    elif row["reason"] != declared_reason:
                        malformed.append(
                            f"{label} has a different reason than its declared exemption"
                        )
                elif section == "population":
                    # The population runner currently declares no per-check
                    # exemptions. Its no-country-route sentinel cannot arise
                    # in a full run; only explicit runner declarations exempt
                    # a check, never a reason supplied by the report itself.
                    declared_reason = population_exemptions.get(
                        (str(row.get("check_id")), str(row.get("route")))
                    )
                    if declared_reason is None:
                        malformed.append(f"{label} is an undeclared unsupported check")
                    elif row["reason"] != declared_reason:
                        malformed.append(
                            f"{label} has a different reason than its declared exemption"
                        )
                unsupported.append(label)
            elif status != "pass":
                malformed.append(f"{label} has unknown status {status!r}")
    if not report.get("cases"):
        malformed.append("the report has no cases")
    # A full run covers what the runner itself declares: every route, every
    # case on each route it runs on, and every sampled property with the
    # examples asked for. A report that drops any of it does not qualify.
    if coverage is None:
        # Lead with the missing runner declarations rather than truncating
        # that root cause behind individual rows whose exemptions are unknown.
        malformed.insert(
            0,
            "the runner declares no ROUTES, CASES and PROPERTIES, so the "
            "report's coverage cannot be checked",
        )
    else:
        reported_routes = [str(route) for route in report.get("routes") or []]
        if sorted(reported_routes) != sorted(coverage["routes"]):
            malformed.append(
                f"the report covers routes {sorted(reported_routes)}, not "
                f"{sorted(coverage['routes'])}"
            )
        covered = {
            (str(row.get("case_id")), str(row.get("route")))
            for row in report.get("cases") or []
        }
        absent = [
            f"{case}@{route}"
            for case, route in coverage["pairs"]
            if (case, route) not in covered
        ]
        if absent:
            malformed.append(
                f"{len(absent)} case-route pair(s) have no row: "
                + ", ".join(absent[:4])
            )
        reported_checks = Counter(
            (str(row.get("case_id")), str(row.get("route")), row.get("check"))
            for row in report.get("cases") or []
        )
        # W1 replaces a case-route's checks with a single error row when
        # constructing its simulation crashes. That is a complete attempted
        # run and already fails the gate; it cannot exempt a passing report.
        crashed = {
            (str(row.get("case_id")), str(row.get("route")))
            for row in report.get("cases") or []
            if row.get("status") == "error"
            and row.get("check") is None
            and row.get("detail")
        }
        absent_checks = (
            Counter(key for key in coverage["checks"] if key[:2] not in crashed)
            - reported_checks
        )
        if absent_checks:
            malformed.append(
                f"{sum(absent_checks.values())} declared case check(s) have no row: "
                + ", ".join(
                    f"{case}@{route}:{check}"
                    for case, route, check in list(absent_checks)[:4]
                )
            )
        # A pending decision belongs to one declared assertion. Count each
        # assertion separately and never let pending rows satisfy mandatory
        # rows, even where the runner reads the same parameter twice.
        for category in ("mandatory", "pending"):
            expected = Counter(
                key
                for key, declaration in coverage["assertions"].items()
                if key[:2] not in crashed
                and (
                    "pending"
                    if declaration["pending"] is not None
                    and key[:3] not in coverage["unsupported_checks"]
                    else "mandatory"
                )
                == category
            )
            actual = Counter(
                reported_assertions[id(row)]
                for row in report.get("cases") or []
                if id(row) in reported_assertions
                and ("pending" if row.get("status") == "pending" else "mandatory")
                == category
            )
            absent_assertions = expected - actual
            excess_assertions = actual - expected
            if absent_assertions or excess_assertions:
                malformed.append(
                    f"{category} assertion multiplicities differ: "
                    f"{sum(absent_assertions.values())} missing, "
                    f"{sum(excess_assertions.values())} extra; "
                    + ", ".join(
                        f"{case}@{route}:{assertion_id}"
                        for case, route, _, assertion_id in list(
                            absent_assertions or excess_assertions
                        )[:4]
                    )
                )
        for case, route in coverage["run_pairs"]:
            rows = [
                row
                for row in report.get("cases") or []
                if row.get("case_id") == case and row.get("route") == route
            ]
            if len(rows) != 1:
                malformed.append(
                    f"run-level check {case}@{route} must have exactly one row"
                )
            elif rows[0].get("status") not in ("pass", "fail", "error"):
                malformed.append(f"run-level check {case}@{route} did not run")
            elif not (rows[0].get("check") or "").startswith(RUN_LEVEL_CHECK_PREFIX):
                malformed.append(
                    f"run-level check {case}@{route} does not identify the shared parameter check"
                )
        for row in report.get("cases") or []:
            key = (str(row.get("case_id")), str(row.get("route")), row.get("check"))
            if key in coverage["isolation_checks"] and row.get("status") not in (
                "pass",
                "fail",
                "error",
            ):
                # The runner emits pass/fail for isolation, never a methodology
                # exemption. An explicit pending-decision override must not
                # excuse a missing executed isolation check.
                malformed.append(
                    f"case {key[0]}@{key[1]} isolation check {key[2]} did not run"
                )
            if row.get("route") in coverage["unsupported_routes"] and (
                row.get("check") is not None or row.get("status") != "unsupported"
            ):
                malformed.append(
                    f"case {row.get('case_id')}@{row.get('route')} is not the declared unsupported route row"
                )
        if dataset_path is not None:
            declared_population = coverage["population"]
            if declared_population is None:
                try:
                    module_name = (
                        entrypoint.partition(":")[0]
                        if ":" in entrypoint
                        else entrypoint.rpartition(".")[0]
                    )
                    declared_population = _declared_population_checks(
                        module_name, importer, coverage["routes"]
                    )
                except (ImportError, AttributeError) as exc:
                    malformed.append(str(exc))
                    declared_population = []
            if not declared_population:
                malformed.append(
                    "the runner declares no population checks, so population coverage cannot be checked"
                )
            else:
                population = Counter(
                    (str(row.get("check_id")), str(row.get("route")))
                    for row in report.get("population") or []
                )
                expected_population = Counter(declared_population)
                absent_population = expected_population - population
                excess_population = population - expected_population
                if absent_population or excess_population:
                    malformed.append(
                        "declared population check route multiplicities differ: "
                        f"{sum(absent_population.values())} missing, "
                        f"{sum(excess_population.values())} extra; "
                        + ", ".join(
                            f"{check}@{route}"
                            for check, route in list(
                                absent_population or excess_population
                            )
                        )
                    )
        properties = {
            str(row.get("property_id")): row for row in report.get("properties") or []
        }
        for name in coverage["properties"]:
            row = properties.get(name)
            if row is None:
                malformed.append(f"property {name} has no row")
            elif row.get("status") == "pass":
                examples = row.get("examples_run")
                if (
                    isinstance(examples, bool)
                    or not isinstance(examples, int)
                    or examples < max_examples
                    or examples < 1
                ):
                    malformed.append(
                        f"property {name} passed on {examples} example(s), "
                        f"not the {max_examples} requested"
                    )
    if dataset_path is not None and not report.get("population"):
        malformed.append("a dataset was given but no population checks ran")
    for field, requested in (("seed", seed), ("max_examples", max_examples)):
        if field in report and report[field] != requested:
            malformed.append(f"the report ran {field}={report[field]}, not {requested}")
    reported_versions = report.get("versions") or {}
    for package, version in (expected_versions or {}).items():
        if reported_versions.get(package) != version:
            malformed.append(
                f"the report ran {package} {reported_versions.get(package)}, "
                f"not the candidate's {version}"
            )
    if expected_dataset_sha256 is not None:
        reported = (report.get("dataset") or {}).get("sha256")
        if reported != expected_dataset_sha256:
            malformed.append(
                f"the report ran dataset {reported}, not the candidate's "
                f"{expected_dataset_sha256}"
            )
    if "holds" in report and report["holds"] != (
        counts["fail"] == 0 and counts["error"] == 0
    ):
        malformed.append("the report's holds disagrees with its rows")
    summary = report.get("summary")
    if (
        isinstance(summary, Mapping)
        and {status: summary.get(status, 0) for status in _CONTRACT_STATUSES} != counts
    ):
        malformed.append("the report's summary disagrees with its rows")
    published = publishable_contract_report(report)
    details = {
        "contract_id": report.get("contract_id"),
        "contract_version": report.get("contract_version"),
        # The digest of what is published: one of the full report would let
        # anyone recover a suppressed count by trying the nine values.
        "report_sha256": evidence_sha256(published),
        "counts": counts,
        "pending": pending,
        "unsupported": unsupported,
        "problems": malformed,
    }
    if failures:
        return _result(
            "reform_contract",
            "fail",
            f"{len(failures)} contract row(s) failed: {', '.join(failures[:8])}",
            published,
            details,
        )
    if malformed:
        return _result(
            "reform_contract", "error", "; ".join(malformed[:8]), published, details
        )
    return _result(
        "reform_contract",
        "pass",
        f"Contract {details['contract_version']}: every case, property and "
        f"population check passed ({counts['pass']})"
        + (f"; {len(pending)} pending a methodology call" if pending else "")
        + (f"; {len(unsupported)} unsupported by design" if unsupported else "")
        + ".",
        published,
        details,
    )


#: Written in place of a value from the survey data that the ledger does
#: not publish.
WITHHELD_VALUE = "withheld"


#: The population row fields W1's runner writes that carry no survey value
#: (``budget_reform_population._row``, its identity fields and the run's
#: fixed subsample size); they are published as reported. ``detail`` goes
#: through ``_publishable_detail``; any other field is withheld.
POPULATION_ROW_FIELDS = frozenset(
    {
        "check_id",
        "route",
        "status",
        "reason",
        "seed",
        "subsample_households",
        "reform_identity",
        "reform_identity_unavailable",
    }
)


def _finding(value: Any) -> Any:
    return value if isinstance(value, bool) or value is None else WITHHELD_VALUE


def _publishable_detail(detail: Any) -> Any:
    """A population row's ``detail`` as the ledger may publish it: its
    top-level true/false findings, with every other value withheld.

    Population rows are computed on the survey data, and their numbers
    combine: rows of one check on different routes share a subsample, so
    two routes' totals or counts differ by what a handful of records did
    (supp-r4 on #574), and two candidates' differ in the same way (cos
    d1601). No per-value rule can bound every combination, and no gate rule
    reads ``detail``. So only ``True``, ``False`` and ``None`` at the top of
    a mapping are published, under the runner's own keys: not counts,
    totals, amounts or text, and no nested list or mapping, whose length or
    keys could be a count or name records (supp-r5).
    """

    if not isinstance(detail, Mapping):
        return _finding(detail)
    return {key: _finding(value) for key, value in detail.items()}


def publishable_contract_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """The reform contract report as the qualification ledger publishes it.

    The ledger is a branch of a public repository. Case and property rows
    come from synthetic households and are published as reported. Population
    rows are computed on the survey data: the fields in
    ``POPULATION_ROW_FIELDS`` (check, route and status, which the gate
    judges, among them) are published as reported, ``detail`` keeps only its
    top-level true/false findings (``_publishable_detail``), and any other
    field is withheld. The gate judges the report as the runner returned it.
    To see a failed population check's figures, rerun the contract with
    access to the dataset (``docs/engineering/runbooks/uk-qualification.md``).
    """

    published = dict(report)
    if isinstance(report.get("population"), list):
        published["population"] = [
            {
                key: value
                if key in POPULATION_ROW_FIELDS
                else (_publishable_detail(value) if key == "detail" else WITHHELD_VALUE)
                for key, value in row.items()
            }
            if isinstance(row, Mapping)
            else row
            for row in report["population"]
        ]
    return published


# --- 9. Metrics review ---------------------------------------------------------


def _metric_key(row: Mapping[str, Any]) -> tuple[str, Optional[int]]:
    return (str(row["metric_id"]), row.get("year"))


def _bound(bounds: Mapping[str, Any], kind: Optional[str]) -> tuple[float, float]:
    spec = (bounds.get("kinds") or {}).get(kind) or bounds.get("default") or {}
    return float(spec.get("relative", 0.0)), float(spec.get("absolute", 0.0))


#: Metric-report check prefixes (``identities[].identity_id``) that fail a
#: candidate whatever the previous pair did: none fail on main.
HARD_CHECK_PREFIXES = (
    "finite:",
    "weights:",
    "closure",
    "identity:",
    "determinism:",
    "reform_runs:",
    "responsive:",
)
#: Checks that already fail on main for known model defects (for example
#: ``counted_once:statutory_sick_pay``): they fail a candidate only when the
#: previous certified pair passed them.
REGRESSION_CHECK_PREFIXES = (
    "counted_once:",
    "double_count_present:",
    "overlap_guard:",
    "sign:",
    "bounds:",
)


#: The statuses the metrics tool gives a check. Anything else fails.
CHECK_STATUSES = frozenset({"pass", "warn", "fail", "skipped"})


def classify_check(identity_id: str) -> str:
    """``hard``, ``regression`` or ``hard`` for an unknown check (no skips)."""

    if identity_id.startswith(REGRESSION_CHECK_PREFIXES):
        return "regression"
    return "hard"


def _suppressed(row: Mapping[str, Any]) -> bool:
    """Whether the tool published ``row`` as suppressed (fewer than 10 records)."""

    return row.get("suppressed") is True


def _excludes(row: Mapping[str, Any]) -> tuple[str, ...]:
    """The suppressed figures a total is rebuilt without, in ``row``'s year."""

    return tuple(sorted(str(metric_id) for metric_id in row.get("excludes") or ()))


#: The fields the pinned tool gives every metric row under its small-cell
#: rule (``api.to_report`` at policyengine-uk 1191ac5a4). A report without
#: them comes from a tool that predates suppression and may publish a figure
#: from fewer than 10 records, so it fails.
SMALL_CELL_FIELDS = ("suppressed", "excludes", "exclude_signs")


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and math.isfinite(value)
    )


def _valid_signs(row: Mapping[str, Any]) -> Optional[dict[str, int]]:
    """``exclude_signs`` when it gives +1 or -1 for exactly the excluded ids."""

    signs, excludes = row.get("exclude_signs"), row.get("excludes")
    if not isinstance(signs, Mapping) or not isinstance(excludes, list):
        return None
    if set(signs) != set(excludes) or not all(
        not isinstance(sign, bool) and sign in (1, -1) for sign in signs.values()
    ):
        return None
    return {str(metric_id): int(sign) for metric_id, sign in signs.items()}


def _small_cell_problems(name: str, rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Rows that break the tool's small-cell format, as problems.

    The tool publishes a figure from fewer than 10 records with ``value``
    null and ``suppressed`` true. A suppressed spending head's caseload is
    suppressed with it; a published head's caseload counts only positive
    records, so it can be suppressed on its own. Every total holding a
    suppressed figure is rebuilt without it; the total lists the figure's
    ``metric_id`` under ``excludes`` and the sign it enters with, +1 or -1,
    under ``exclude_signs`` (``privacy.py``, ``measure.measure_year`` and
    ``measure.rebuild_protected`` in the pinned tool). These are reports this
    gate cannot read safely, so neither the gate's evidence nor the ledger
    records any value from them:

    - a row without the small-cell fields, or whose year is not an integer;
    - two rows for one figure and year (one could publish what the other
      suppresses);
    - a suppressed row with a value, or a ``suppressed`` that is not a
      boolean;
    - an ``excludes`` that is not a list of ids, or names a figure the same
      report does not suppress in that year;
    - ``exclude_signs`` that do not give +1 or -1 for exactly ``excludes``;
    - a published caseload beside its suppressed spending head.
    """

    by_key = {(str(row.get("metric_id")), row.get("year")): row for row in rows}
    hidden = {key for key, row in by_key.items() if _suppressed(row)}
    repeated = sorted(
        f"{key[0]} {key[1]}"
        for key, count in Counter(
            (str(row.get("metric_id")), row.get("year")) for row in rows
        ).items()
        if count > 1
    )
    missing_fields, bad_years, with_value, not_boolean = [], [], [], []
    malformed, bad_signs, unmatched, unpaired = [], [], [], []
    for row in rows:
        metric_id, year = str(row.get("metric_id")), row.get("year")
        label = f"{metric_id} {year}"
        if any(field not in row for field in SMALL_CELL_FIELDS):
            missing_fields.append(label)
        if isinstance(year, bool) or not isinstance(year, int):
            bad_years.append(label)
        flag = row.get("suppressed", False)
        if not isinstance(flag, bool):
            not_boolean.append(label)
        elif flag and row.get("value") is not None:
            with_value.append(label)
        if metric_id.startswith("caseloads.") and not _suppressed(row):
            head = by_key.get((f"spending.{metric_id.split('.', 1)[1]}", year))
            if head is not None and _suppressed(head):
                unpaired.append(label)
        excludes = row.get("excludes", [])
        if not isinstance(excludes, list) or not all(
            isinstance(excluded, str) for excluded in excludes
        ):
            malformed.append(label)
            continue
        if "exclude_signs" in row and _valid_signs(row) is None:
            bad_signs.append(label)
        unmatched.extend(
            f"{label} excludes {excluded}"
            for excluded in excludes
            if (excluded, year) not in hidden
        )
    problems = []
    for found, what in (
        (
            missing_fields,
            "rows without the small-cell fields (suppressed, excludes, "
            "exclude_signs), so from a tool that predates suppression",
        ),
        (bad_years, "metric rows whose year is not an integer"),
        (repeated, "duplicate metrics"),
        (with_value, "suppressed figures with a value"),
        (not_boolean, "a suppressed flag that is not true or false"),
        (malformed, "excludes that are not a list of metric ids"),
        (bad_signs, "exclude_signs that are not +1 or -1 for exactly its excludes"),
        (unmatched, "totals excluding a figure it does not suppress"),
        (unpaired, "caseloads published beside their suppressed spending head"),
    ):
        if found:
            problems.append(f"the {name} report has {what}: {', '.join(found[:8])}")
    return problems


#: Totals that are plain sums of heads in pounds, so a figure can be taken out
#: by subtraction: the pinned tool's ``compare._additive`` (sections
#: model_totals and balance, whose rows have kind ``model_total`` and
#: ``balance``, and household net income). Decile means and the HBAI total
#: (reset at zero) are not.
ADDITIVE_KINDS = frozenset({"model_total", "balance"})
ADDITIVE_METRICS = frozenset({"household.household_net_income"})


def _additive(row: Mapping[str, Any]) -> bool:
    return (
        row.get("kind") in ADDITIVE_KINDS
        or str(row.get("metric_id")) in ADDITIVE_METRICS
    )


def _aligned(
    value: float,
    own: Mapping[str, Any],
    other_signs: Mapping[str, int],
    metrics: Mapping[tuple[str, Optional[int]], Mapping[str, Any]],
    year: Optional[int],
) -> Optional[float]:
    """``own``'s total with every figure only the other side excludes taken out.

    As ``compare._aligned`` in the pinned tool: the figure's value is this
    side's own published row for the year, and its sign is the one the side
    that excludes it records. None when a needed figure is not published
    here (missing, suppressed or not finite).
    """

    own_excludes = set(_excludes(own))
    for metric_id, sign in sorted(other_signs.items()):
        if metric_id in own_excludes:
            continue
        published = metrics.get((metric_id, year))
        if (
            published is None
            or _suppressed(published)
            or not _finite_number(published.get("value"))
        ):
            return None
        value -= sign * float(published["value"])
    return value


def _wider_failure(candidate: Mapping[str, Any], previous: Mapping[str, Any]) -> bool:
    """Whether a check failing in both reports fails in a scope it did not before.

    Scopes are years, or ``""`` for a check with no year. Without
    ``failing_scopes`` on both rows the two failures cannot be told apart, so
    the failure counts as carried over.
    """

    now, before = candidate.get("failing_scopes"), previous.get("failing_scopes")
    if not isinstance(now, list) or not isinstance(before, list):
        return False
    return not {str(scope) for scope in now} <= {str(scope) for scope in before}


def compare_metric_reports(
    candidate: Mapping[str, Any],
    previous: Mapping[str, Any],
    bounds: Mapping[str, Any],
) -> tuple[str, str, Evidence]:
    """``(status, summary, evidence)`` for a candidate against a previous report.

    Checks (``identities``) follow the metric tool's classification: hard
    checks fail outright; known-defect checks fail only when they worsen
    against the previous pair, meaning the previous pair did not fail them,
    or failed them in fewer scopes (``failing_scopes``, when the tool reports
    them); ``warn`` is recorded, and a check that newly warns (it did not
    warn in the previous report, as the tool's ``new_warning``) needs
    review. ``skipped`` means the check was not run, which is neither a pass
    nor a failure: a skipped hard check, or a check skipped where the
    previous pair ran it (pass, warn or fail), needs review.

    A report with a status other than ``ok``, no metrics or no checks fails,
    as does a report that repeats a check, or any check, in either report,
    with a status outside ``CHECK_STATUSES``. A hard check the previous pair
    ran that is missing from the candidate fails (the two reports share one
    tool and one set of definitions); other missing checks need review.

    Small cells (W3's tool publishes a figure from fewer than 10 records as
    ``value`` null, ``suppressed`` true, and rebuilds every total that holds
    one without it, listing it under ``excludes`` with its sign under
    ``exclude_signs``):

    - a suppressed figure is present but never compared, and is not a
      non-finite value; suppressed on both sides, there is nothing to compare;
    - a figure suppressed on one side only is withheld: no change is
      computed (it would come from fewer than 10 records) and the comparison
      needs review;
    - a total compares directly when both sides exclude the same figures
      with the same signs;
    - an additive total (``_additive``) whose sides exclude different
      figures is lined up as the tool's ``compare._aligned`` does: each side
      takes out, at its own published value and the excluding side's sign,
      every figure only the other side excludes. The change between the
      lined-up totals is held to the bound, whose relative part is taken on
      the previous report's published total. Any other total with different
      exclusions, or one that cannot be lined up (a needed figure not
      published, or a figure both sides exclude with different signs), is
      withheld for review;
    - a report that breaks the format (``_small_cell_problems``) fails.
    """

    problems: list[str] = []
    review: list[str] = []
    # An empty or unfinished report measures nothing; it must never read as
    # "no moves beyond the bounds".
    for name, report in (("candidate", candidate), ("previous", previous)):
        if report.get("status") != "ok":
            problems.append(f"the {name} report status is {report.get('status')!r}")
        if not report.get("metrics"):
            problems.append(f"the {name} report has no metrics")
        if not report.get("identities"):
            problems.append(f"the {name} report has no checks")
        # One row per check: a repeated id would let either copy decide.
        check_counts = Counter(
            str(row.get("identity_id")) for row in report.get("identities", [])
        )
        repeated = sorted(check for check, count in check_counts.items() if count > 1)
        if repeated:
            problems.append(
                f"the {name} report repeats checks: {', '.join(repeated[:8])}"
            )
    # The previous report's statuses decide regressions and new warnings, so
    # an unknown one there is no more a pass than in the candidate.
    previous_unknown = [
        f"{row.get('identity_id')} ({row.get('status')!r})"
        for row in previous.get("identities", [])
        if row.get("status") not in CHECK_STATUSES
    ]
    if previous_unknown:
        problems.append(
            "the previous report has checks with an unknown status: "
            + ", ".join(previous_unknown[:8])
        )
    previous_rows = {
        str(row.get("identity_id")): row for row in previous.get("identities", [])
    }
    hard_failures: list[str] = []
    regressions: list[str] = []
    preexisting: list[str] = []
    new_warnings: list[str] = []
    warnings_: list[str] = []
    skipped: list[str] = []
    newly_skipped: list[str] = []
    hard_skipped: list[str] = []
    unknown_statuses: list[str] = []
    candidate_checks = set()
    for row in candidate.get("identities", []):
        check_id = str(row.get("identity_id"))
        candidate_checks.add(check_id)
        status = row.get("status")
        earlier = previous_rows.get(check_id) or {}
        before = earlier.get("status")
        if status not in CHECK_STATUSES:
            unknown_statuses.append(f"{check_id} ({status!r})")
        elif status == "fail":
            if classify_check(check_id) == "hard":
                hard_failures.append(check_id)
            elif before != "fail":
                regressions.append(check_id)
            elif _wider_failure(row, earlier):
                regressions.append(f"{check_id} (fails in more scopes)")
            else:
                preexisting.append(check_id)
        elif status == "warn":
            warnings_.append(check_id)
            if before != "warn":
                new_warnings.append(check_id)
        elif status == "skipped":
            # Not run: never a pass, whatever the check's class.
            skipped.append(check_id)
            if classify_check(check_id) == "hard":
                hard_skipped.append(check_id)
            if before in ("pass", "warn", "fail"):
                newly_skipped.append(check_id)
    if unknown_statuses:
        # A status this gate does not know is not a pass.
        problems.append(
            f"checks with an unknown status: {', '.join(unknown_statuses[:8])}"
        )
    # A check the previous pair ran and the candidate did not: the tool and
    # its definitions are the same (metrics_version), so coverage was lost.
    lost_checks = sorted(set(previous_rows) - candidate_checks)
    lost_hard = [
        check_id
        for check_id in lost_checks
        if classify_check(check_id) == "hard"
        and candidate.get("partition_version") == previous.get("partition_version")
    ]
    if lost_hard:
        problems.append(f"checks disappeared: {', '.join(lost_hard[:8])}")
    elif lost_checks:
        review.append(f"checks disappeared: {', '.join(lost_checks[:8])}")
    if hard_failures:
        problems.append(f"checks failed: {', '.join(hard_failures[:8])}")
    if regressions:
        problems.append(
            f"checks the previous pair passed now fail: {', '.join(regressions[:8])}"
        )
    if new_warnings:
        review.append(f"checks newly warn: {', '.join(new_warnings[:8])}")
    if newly_skipped:
        review.append(
            "checks the previous pair ran were not run: " + ", ".join(newly_skipped[:8])
        )
    if hard_skipped:
        review.append(f"hard checks were not run: {', '.join(hard_skipped[:8])}")
    if candidate.get("metrics_version") != previous.get("metrics_version"):
        problems.append(
            "metric definitions differ between the reports "
            f"({previous.get('metrics_version')} → {candidate.get('metrics_version')})"
        )
    if candidate.get("partition_version") != previous.get("partition_version"):
        review.append("the model's fiscal partition changed")
    current = {_metric_key(row): row for row in candidate.get("metrics", [])}
    before_metrics = {_metric_key(row): row for row in previous.get("metrics", [])}
    # Bounds are meaningful only when both sides contain usable values.
    # In particular, NaN in the baseline must not silently skip a large move.
    report_metric_rows = (
        ("candidate", candidate.get("metrics", [])),
        ("previous", previous.get("metrics", [])),
    )
    unsafe = False
    for name, rows in report_metric_rows:
        # A suppressed figure is published without a value by design.
        nonfinite = [
            f"{row.get('metric_id')} {row.get('year')}"
            for row in rows
            if not _suppressed(row) and not _finite_number(row.get("value"))
        ]
        if nonfinite:
            problems.append(
                f"the {name} report has non-finite values: {', '.join(nonfinite[:8])}"
            )
        format_problems = _small_cell_problems(name, rows)
        problems.extend(format_problems)
        unsafe = unsafe or bool(format_problems)
    lost = sorted(f"{key[0]} {key[1]}" for key in set(before_metrics) - set(current))
    if lost:
        problems.append(f"metrics disappeared: {', '.join(lost[:8])}")
    without_baseline = sorted(
        f"{key[0]} {key[1]}" for key in set(current) - set(before_metrics)
    )
    if without_baseline:
        review.append(f"metrics have no baseline: {', '.join(without_baseline[:8])}")
    moves = []
    withheld: list[dict[str, Any]] = []
    aligned_totals: list[str] = []
    suppressed_on_both = 0
    # A report that breaks the small-cell format may carry a figure from
    # fewer than 10 records: it fails above, and no value from either report
    # enters the evidence, which the public ledger publishes.
    comparable = {} if unsafe else current
    # Years sort as text so a malformed year (failed above) cannot crash this.
    for key, row in sorted(
        comparable.items(), key=lambda item: (item[0][0], str(item[0][1]))
    ):
        old = before_metrics.get(key)
        if old is None:
            continue
        if _suppressed(row) and _suppressed(old):
            suppressed_on_both += 1
            continue
        if _suppressed(row) or _suppressed(old):
            # A figure from fewer than 10 records on one side: so is its change.
            withheld.append(
                {
                    "metric_id": key[0],
                    "year": key[1],
                    "reason": "suppressed in the "
                    + ("candidate" if _suppressed(row) else "previous")
                    + " report",
                }
            )
            continue
        if not (_finite_number(row.get("value")) and _finite_number(old.get("value"))):
            continue
        new_value, old_value = float(row["value"]), float(old["value"])
        new_compared, old_compared = new_value, old_value
        aligned_on: Optional[list[str]] = None
        # Both reports passed the format check, so their signs are valid.
        new_signs, old_signs = _valid_signs(row) or {}, _valid_signs(old) or {}
        if new_signs != old_signs:
            # Each side leaves out its own suppressed figures, each with its
            # sign (the tool compares the signed maps, whose keys are the
            # excluded ids). Subtracting the totals as published would mix
            # definitions and could give an excluded figure back, so they are
            # lined up first, from published figures only, or withheld.
            reason = None
            if any(
                new_signs[metric_id] != old_signs[metric_id]
                for metric_id in set(new_signs) & set(old_signs)
            ):
                reason = (
                    "a figure both reports leave out enters their totals "
                    "with different signs"
                )
            elif not (_additive(row) and _additive(old)):
                reason = "the reports leave out different suppressed figures"
            else:
                lined_up = (
                    _aligned(new_value, row, old_signs, current, key[1]),
                    _aligned(old_value, old, new_signs, before_metrics, key[1]),
                )
                if lined_up[0] is None or lined_up[1] is None:
                    reason = (
                        "the reports leave out different suppressed figures, "
                        "and one needed to line them up is not published"
                    )
                else:
                    new_compared, old_compared = lined_up
                    aligned_on = sorted(set(new_signs) | set(old_signs))
                    aligned_totals.append(f"{key[0]} {key[1]}")
            if reason is not None:
                withheld.append(
                    {
                        "metric_id": key[0],
                        "year": key[1],
                        "reason": reason,
                        "candidate_excludes": list(_excludes(row)),
                        "previous_excludes": list(_excludes(old)),
                    }
                )
                continue
        relative, absolute = _bound(bounds, row.get("kind"))
        # The relative part is taken on the previous published total, as the
        # tool's flag threshold is.
        threshold = max(relative * abs(old_value), absolute)
        change = new_compared - old_compared
        if abs(change) > threshold:
            move = {
                "metric_id": key[0],
                "year": key[1],
                "kind": row.get("kind"),
                "previous": old_value,
                "candidate": new_value,
                "change": change,
                "threshold": threshold,
            }
            if aligned_on is not None:
                move["lined_up_without"] = aligned_on
            moves.append(move)
    if moves:
        review.append(f"{len(moves)} metric move(s) exceed their review bounds")
    if withheld:
        review.append(
            f"{len(withheld)} metric change(s) are withheld because a figure "
            "from fewer than 10 records is suppressed on one side, or the two "
            "sides leave out different ones and cannot be lined up"
        )
    evidence = {
        "metrics_version": candidate.get("metrics_version"),
        "partition_version": candidate.get("partition_version"),
        "previous_partition_version": previous.get("partition_version"),
        "hard_check_failures": hard_failures,
        "regressed_checks": regressions,
        "preexisting_check_failures": preexisting,
        "warn_identities": warnings_,
        "new_warnings": new_warnings,
        "skipped_checks": skipped,
        "newly_skipped_checks": newly_skipped,
        "hard_checks_not_run": hard_skipped,
        "unknown_status_checks": unknown_statuses,
        "lost_checks": lost_checks,
        "metrics_without_baseline": without_baseline,
        "suppressed_metrics": sorted(
            f"{key[0]} {key[1]}" for key, row in current.items() if _suppressed(row)
        ),
        "suppressed_on_both_sides": suppressed_on_both,
        "withheld_changes": withheld,
        "lined_up_totals": aligned_totals,
        # True when a report breaks the small-cell format: no value from
        # either report was compared or recorded.
        "values_withheld": unsafe,
        "moves_beyond_bounds": moves,
        "candidate_report_sha256": evidence_sha256(candidate),
        "previous_report_sha256": evidence_sha256(previous),
    }
    if problems:
        return "fail", "; ".join(problems), evidence
    if review:
        return "needs_review", "; ".join(review), evidence
    notes = []
    if suppressed_on_both:
        notes.append(f"{suppressed_on_both} suppressed on both sides, not compared")
    if preexisting:
        notes.append(f"{len(preexisting)} known check failures carried over")
    note = f" ({'; '.join(notes)})" if notes else ""
    compared = len(current) - suppressed_on_both
    return "pass", f"{compared} metrics within their review bounds{note}.", evidence


def metrics_review(
    *,
    candidate_report: Optional[Mapping[str, Any]],
    previous_report: Optional[Mapping[str, Any]],
    bounds: Mapping[str, Any],
    cross_report: Optional[Mapping[str, Any]] = None,
    unavailable_reason: Optional[str] = None,
) -> GateOutcome:
    """Compare metrics against the previous certificate under review bounds.

    With ``cross_report`` (the candidate model on the previous data), the
    change splits into a model-only step (cross against previous) and a
    data-only step (candidate against cross); the gate takes the worse.
    """

    if unavailable_reason or candidate_report is None or previous_report is None:
        return _result(
            "metrics_review",
            "unavailable",
            unavailable_reason or "Metric reports for both pairs are not available.",
            {},
        )
    order = {"pass": 0, "needs_review": 1, "fail": 2}
    steps: dict[str, tuple[str, str, Evidence]] = {}
    if cross_report is not None:
        steps["model_only"] = compare_metric_reports(
            cross_report, previous_report, bounds
        )
        steps["data_only"] = compare_metric_reports(
            candidate_report, cross_report, bounds
        )
    else:
        steps["total"] = compare_metric_reports(
            candidate_report, previous_report, bounds
        )
    worst = max(steps.values(), key=lambda step: order[step[0]])
    evidence = {name: step[2] for name, step in steps.items()}
    summary = "; ".join(f"{name}: {step[1]}" for name, step in steps.items())
    return _result(
        "metrics_review",
        worst[0],
        summary,
        evidence,
        details={name: step[0] for name, step in steps.items()},
    )


def publishable_metrics_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """A metrics report as it may be written to the qualification ledger.

    The ledger is a branch of a public repository. A report that breaks the
    small-cell format (``_small_cell_problems``) may carry a figure from
    fewer than 10 records, so only its digest and its problems, which name
    figures but give no values, are kept. A report the tool could not finish
    has no metrics to check and is kept as it is.
    """

    problems = _small_cell_problems("metrics", report.get("metrics") or [])
    if not problems:
        return dict(report)
    return {
        "withheld": (
            "This report breaks the metrics tool's small-cell format, so it "
            "is not published."
        ),
        "report_sha256": evidence_sha256(report),
        "problems": problems,
    }


# --- Reform responsiveness -------------------------------------------------------


def _fiscal_year(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def reform_responsiveness(
    *,
    report: Optional[Mapping[str, Any]],
    standard_reforms: Sequence[Mapping[str, Any]],
    years: Sequence[int],
    unavailable_reason: Optional[str] = None,
) -> GateOutcome:
    """Every standard reform ran and moved its target as required, or fail.

    The metrics tool costs its standard reforms and, for each, checks that
    the weighted total of the reform's target variable moved in the stated
    direction by at least the stated minimum in every year
    (``responsive:<id>``), and that the reform ran (``reform_runs:<id>``).
    This gate holds the candidate's report to that:

    - both checks must be present and ``pass`` for every reform in
      ``standard_reforms`` (the tool's own list); a missing check is a
      failure, so a run that costed no reforms cannot pass;
    - the report must cover exactly ``years``;
    - the tool's verdict is recomputed here from the report's
      ``reform_targets.<id>`` values, and a disagreement is an error
      (differential check of the check).

    Any reform that does not respond fails the gate: a reform the model
    silently ignores is a defect, never a small number. The one review path
    is a year the tool withholds (``reform_targets.<id>`` published as
    suppressed, because the change would come from fewer than 10 records):
    there the tool's verdict, which it takes from the withheld value, cannot
    be recomputed, so a passing ``responsive`` check needs review rather
    than passing; a failing one still fails. The gate is monotone: shrinking
    a reform's response toward zero or flipping its sign never turns a
    failure into a pass.
    """

    if unavailable_reason or report is None:
        return _result(
            "reform_responsiveness",
            "unavailable",
            unavailable_reason or "No candidate metrics report is available.",
            {},
        )
    if not standard_reforms:
        return _result(
            "reform_responsiveness",
            "unavailable",
            "The metrics tool defines no standard reforms.",
            {},
        )
    checks = {
        str(row.get("identity_id")): row for row in report.get("identities") or []
    }
    rows = {
        (str(row.get("metric_id")), row.get("year")): row
        for row in report.get("metrics") or []
    }
    problems: list[str] = []
    disagreements: list[str] = []
    unverifiable: list[str] = []
    table: list[dict[str, Any]] = []
    if report.get("status") not in (None, "ok"):
        problems.append(f"the report status is {report.get('status')!r}")
    if sorted(report.get("years") or []) != sorted(years):
        disagreements.append(
            f"the report covers {report.get('years')}, not the horizon {list(years)}"
        )
    # A repeated target or check would let either copy decide.
    repeated = sorted(
        f"{key[0]} {key[1]}"
        for key, count in Counter(
            (str(row.get("metric_id")), row.get("year"))
            for row in report.get("metrics") or []
        ).items()
        if count > 1 and key[0].startswith("reform_targets.")
    ) + sorted(
        check
        for check, count in Counter(
            str(row.get("identity_id")) for row in report.get("identities") or []
        ).items()
        if count > 1 and check.startswith(("reform_runs:", "responsive:"))
    )
    if repeated:
        disagreements.append(f"the report repeats {', '.join(repeated[:8])}")
    # A report that breaks the small-cell format may carry a figure from
    # fewer than 10 records: no value from it enters the evidence.
    format_problems = _small_cell_problems("candidate", report.get("metrics") or [])
    disagreements.extend(format_problems)
    malformed: list[str] = []
    for reform in standard_reforms:
        reform_id = reform["id"]
        sign = 1.0 if reform["direction"] == "up" else -1.0
        changes: dict[str, Any] = {}
        withheld_years: list[int] = []
        # True: every year meets the minimum; False: a published year does
        # not; None: every published year does, but a year is withheld.
        recomputed: Optional[bool] = True
        for year in years:
            target = rows.get((f"reform_targets.{reform_id}", year)) or {}
            value = target.get("value")
            if _suppressed(target):
                # Never copied into evidence, whatever the row carries.
                changes[str(year)] = None
                if value is None:
                    withheld_years.append(year)
                else:
                    malformed.append(f"reform_targets.{reform_id} {year}")
                    recomputed = False
                continue
            changes[str(year)] = None if format_problems else value
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                or not sign * value >= reform["minimum"]
            ):
                recomputed = False
        if recomputed and withheld_years:
            recomputed = None
        ran = (checks.get(f"reform_runs:{reform_id}") or {}).get("status")
        responsive = checks.get(f"responsive:{reform_id}") or {}
        row = {
            **reform,
            "target_changes": changes,
            "withheld_years": withheld_years,
            "reform_runs": ran,
            "responsive": responsive.get("status"),
            # The tool's text can quote amounts; none from an unsafe report.
            "detail": None if format_problems else responsive.get("detail"),
        }
        table.append(row)
        label = f"{reform['name']} ({reform_id})"
        if ran != "pass":
            problems.append(f"{label} did not run")
        elif responsive.get("status") != "pass":
            problems.append(
                f"{label} did not respond: "
                + (
                    row["detail"]
                    or (
                        "its detail is withheld"
                        if format_problems and responsive
                        else "no responsive check in the report"
                    )
                )
            )
        if ran == "pass" and responsive.get("status") in ("pass", "fail"):
            passed = responsive["status"] == "pass"
            if recomputed is None:
                # A failing verdict may come from a withheld year; a passing
                # one cannot be checked there.
                if passed:
                    unverifiable.append(
                        f"{label}: the tool's responsive check passes but "
                        + ", ".join(_fiscal_year(year) for year in withheld_years)
                        + " are withheld (fewer than 10 records), so it cannot "
                        "be recomputed there"
                    )
            elif passed != recomputed:
                disagreements.append(
                    f"{label}: the tool's responsive check is "
                    f"{responsive['status']} but its reform_targets values "
                    f"{'meet' if recomputed else 'do not meet'} the minimum"
                )
    if malformed:
        disagreements.append(
            "suppressed reform targets carry a value: " + ", ".join(malformed[:8])
        )
    evidence = {
        "years": list(years),
        "reforms": table,
        "candidate_report_sha256": evidence_sha256(report),
    }
    if problems:
        return _result(
            "reform_responsiveness",
            "fail",
            f"{len(problems)} responsiveness failure(s): " + "; ".join(problems[:6]),
            evidence,
        )
    if disagreements:
        return _result(
            "reform_responsiveness", "error", "; ".join(disagreements[:6]), evidence
        )
    if unverifiable:
        return _result(
            "reform_responsiveness",
            "needs_review",
            "; ".join(unverifiable[:6]),
            evidence,
        )
    return _result(
        "reform_responsiveness",
        "pass",
        f"All {len(table)} standard reforms ran and moved their targets by at "
        f"least their minimums in every year from {_fiscal_year(years[0])} to "
        f"{_fiscal_year(years[-1])}.",
        evidence,
    )


# --- Metrics tool (W3's aggregate-impact report) ---------------------------------

VENDORED_TOOL_PACKAGE = "pe_uk_aggregate_impact"
PARTITION_PATH_IN_REPO = "policyengine_uk/data/fiscal_partition.yaml"

#: Self-contained runner, executed in any environment that has a policyengine
#: release installed (the candidate's, or the previous certified pair's
#: throwaway venv). Arguments: vendor root, JSON settings, output path.
METRICS_RUNNER = """
import importlib, importlib.util, json, sys
from pathlib import Path
vendor, settings, out = sys.argv[1], json.loads(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, vendor)
api = importlib.import_module("pe_uk_aggregate_impact.api")
partition_module = importlib.import_module("pe_uk_aggregate_impact.partition")
installed = partition_module.default_partition_path()
if installed is not None:
    partition_path, source = installed, "installed policyengine_uk"
else:
    partition_path, source = Path(vendor) / "fiscal_partition.yaml", "vendored tool commit"
dataset = settings.get("dataset_path")
if not dataset:
    from policyengine.provenance.dataset_materialization import materialize_dataset
    dataset = materialize_dataset("uk", data_dir=Path(settings["data_dir"])).path
from policyengine_uk import Microsimulation
# No ``reforms`` argument: the tool then costs its own standard set and checks
# each reform's responsiveness (passing [] would cost none).
report = api.compute_budget_metrics(
    Microsimulation(dataset=str(dataset)),
    years=settings["years"],
    partition=partition_module.load_partition(partition_path),
    run_guard=settings.get("run_guard", True),
    label=settings.get("label", "candidate"),
)
report["partition_source"] = source
report["dataset_path"] = str(dataset)
out.write_text(json.dumps(report))
"""


#: Runner for a pair's input coverage and supported years, in its own
#: environment. It mirrors ``budget_inputs`` and ``supported_years``; a
#: differential test checks they agree. Arguments: JSON settings, output path.
INPUTS_RUNNER = """
import json, sys
from pathlib import Path
import pandas as pd
settings, out = json.loads(sys.argv[1]), Path(sys.argv[2])
path = settings.get("dataset_path")
if not path:
    from policyengine.provenance.dataset_materialization import materialize_dataset
    path = str(materialize_dataset("uk", data_dir=Path(settings["data_dir"])).path)
inputs = settings.get("model_input_variables")
model_names = settings.get("model_variables")
if inputs is None:
    from policyengine_uk.system import system
    inputs = [name for name, variable in system.variables.items() if variable.is_input_variable()]
    model_names = list(system.variables)
inputs = set(inputs)
model_names = inputs | set(model_names or [])
with pd.HDFStore(path, mode="r") as store:
    tables = {e: store[e] for e in ("person", "benunit", "household") if f"/{e}" in store}
    first_year = int(str(store["time_period"].iloc[0])[:4])
columns = {}
for entity, table in tables.items():
    for column in table.columns:
        columns.setdefault(column, entity)
def degenerate(series):
    values = series.dropna()
    if len(values) == 0 or values.nunique() <= 1:
        return True
    if values.dtype.kind in "biuf":
        return bool((values.astype(float) == 0).all())
    return False
unusable = []
for name in settings["critical"]:
    if name not in columns:
        unusable.append([name, "missing"])
    elif degenerate(tables[columns[name]][name]):
        unusable.append([name, "degenerate"])
years = settings.get("projected_years")
if years is None:
    from policyengine_uk.data.dataset_schema import UKSingleYearDataset
    from policyengine_uk.data.economic_assumptions import extend_single_year_dataset
    from policyengine_uk.system import system
    multi_year = extend_single_year_dataset(UKSingleYearDataset(path), system.parameters)
    years = getattr(multi_year, "years", None)
    years = years if years is not None else list(multi_year.datasets)
years = sorted(int(y) for y in years)
out.write_text(json.dumps({
    "dataset_path": path,
    "model_input_variables": len(inputs),
    "model_variables": len(model_names),
    "dataset_columns": len(columns),
    "missing_inputs": sorted(inputs - set(columns)),
    "unusable_critical": unusable,
    "supported_years": [y for y in years if y >= first_year],
    "input_status": {
        name: {
            "in_model": name in model_names,
            "is_input": name in inputs,
            "in_data": name in columns,
            "usable": name in model_names and name in columns and not degenerate(tables[columns[name]][name]),
        }
        for name in sorted(model_names | set(columns))
    },
}))
"""


def run_inputs_snapshot(
    python: str,
    *,
    critical: Sequence[str],
    out: Path,
    dataset_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
    model_input_variables: Optional[Sequence[str]] = None,
    model_variables: Optional[Sequence[str]] = None,
    projected_years: Optional[Sequence[int]] = None,
    run: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Input coverage and supported years of a pair, via ``INPUTS_RUNNER``.

    ``model_input_variables`` and ``projected_years`` default to what the
    environment's policyengine-uk reports; tests pass them explicitly.
    """

    import subprocess

    run = run if run is not None else subprocess.run
    settings = {
        "critical": list(critical),
        "dataset_path": str(dataset_path) if dataset_path else None,
        "data_dir": str(data_dir) if data_dir else None,
        "model_input_variables": (
            list(model_input_variables) if model_input_variables is not None else None
        ),
        "model_variables": list(model_variables)
        if model_variables is not None
        else None,
        "projected_years": list(projected_years)
        if projected_years is not None
        else None,
    }
    run(
        [python, "-c", INPUTS_RUNNER, json.dumps(settings), str(out)],
        check=True,
        cwd=str(out.parent),
    )
    snapshot: dict[str, Any] = json.loads(out.read_text())
    return snapshot


def vendor_metrics_tool(
    tool: Mapping[str, Any], destination: Path, *, get: Callable[..., Any]
) -> Path:
    """Copy the metrics tool and its partition from one policyengine-uk commit.

    Returns the directory to put on ``sys.path``; the tool imports as
    ``pe_uk_aggregate_impact``. The commit is pinned in the qualification
    config so both pairs are measured with the same definitions.
    """

    import tarfile

    repository = tool["repository"]
    commit = tool["commit"]
    tool_path = tool["path"].rstrip("/")
    root = destination / f"metrics-tool-{commit[:12]}"
    package = root / VENDORED_TOOL_PACKAGE
    if (package / "api.py").exists():
        return root
    response = get(
        f"https://codeload.github.com/{repository}/tar.gz/{commit}", timeout=120
    )
    response.raise_for_status()
    package.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
        for member in archive.getmembers():
            _, _, relative = member.name.partition("/")
            if not member.isfile():
                continue
            if relative.startswith(tool_path + "/"):
                target = package / relative[len(tool_path) + 1 :]
            elif relative == PARTITION_PATH_IN_REPO:
                target = root / "fiscal_partition.yaml"
            else:
                continue
            if ".." in Path(relative).parts:
                raise ValueError(f"Unsafe path in the tool archive: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = archive.extractfile(member)
            assert extracted is not None
            target.write_bytes(extracted.read())
    if not (package / "api.py").exists():
        raise ValueError(f"{repository}@{commit} has no {tool_path}/api.py.")
    return root


def load_standard_reforms(vendor_root: Path, filename: str) -> list[dict[str, Any]]:
    """The metrics tool's standard reform set, read from the vendored tool.

    Each entry must carry an ``id`` and a ``responds`` block (``variable``,
    ``direction`` ``up`` or ``down``, positive ``minimum``): a standard reform
    with no stated response cannot be held to one, so it is refused.
    """

    import yaml  # type: ignore[import-untyped]

    path = vendor_root / VENDORED_TOOL_PACKAGE / filename
    if not path.exists():
        raise ValueError(f"The metrics tool ships no {filename}.")
    document = yaml.safe_load(path.read_text()) or {}
    reforms: list[dict[str, Any]] = []
    for entry in document.get("reforms") or []:
        responds = entry.get("responds") or {}
        minimum = responds.get("minimum")
        if (
            not entry.get("id")
            or not responds.get("variable")
            or responds.get("direction") not in ("up", "down")
            or isinstance(minimum, bool)
            or not isinstance(minimum, int | float)
            or not minimum > 0
        ):
            raise ValueError(
                f"Standard reform {entry.get('id') or entry.get('name')!r} states "
                "no id or no expected response."
            )
        reforms.append(
            {
                "id": str(entry["id"]),
                "name": str(entry.get("name") or entry["id"]),
                "variable": str(responds["variable"]),
                "direction": responds["direction"],
                "minimum": float(minimum),
            }
        )
    ids = [reform["id"] for reform in reforms]
    if len(set(ids)) != len(ids):
        raise ValueError("The standard reform set repeats an id.")
    return reforms


def run_metrics_report(
    python: str,
    vendor_root: Path,
    *,
    years: Sequence[int],
    out: Path,
    dataset_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
    run_guard: bool = True,
    label: str = "candidate",
    run: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Compute a metrics report with ``python`` (any environment) via the runner.

    The tool also costs its standard reform set against the same baseline,
    each reform as a full run over ``years``.
    """

    import subprocess

    run = run if run is not None else subprocess.run
    settings = {
        "years": list(years),
        "dataset_path": str(dataset_path) if dataset_path else None,
        "data_dir": str(data_dir) if data_dir else None,
        "run_guard": run_guard,
        "label": label,
    }
    run(
        [
            python,
            "-c",
            METRICS_RUNNER,
            str(vendor_root),
            json.dumps(settings),
            str(out),
        ],
        check=True,
        cwd=str(out.parent),
    )
    report: dict[str, Any] = json.loads(out.read_text())
    return report


class PreviousPairUnavailable(ValueError):
    """The exact certified baseline cannot be constructed or verified."""


def _previous_pair_pins(
    previous: Mapping[str, Any], ledger_root: Optional[Path] = None
) -> dict[str, Any]:
    """Certificate pins, completed by its exact ledger receipt when available."""

    pins = dict(previous)
    pair_id = previous.get("qualification_pair_id")
    if ledger_root is not None and pair_id:
        try:
            receipt = QualificationReceipt.model_validate_json(
                (
                    ledger_root / "uk" / pair_id / "qualification_receipt.json"
                ).read_text()
            )
        except (OSError, ValueError) as exc:
            raise PreviousPairUnavailable(
                "The previous pair's ledger receipt is unavailable."
            ) from exc
        pair = receipt.pair
        expected = {
            "model_version": pair.model.version,
            "core_version": pair.core.version,
            "data_release_version": pair.data.release_version,
            "dataset_sha256": pair.data.dataset_sha256,
            "model_wheel_sha256": pair.model.wheel_sha256,
            "core_wheel_sha256": pair.core.wheel_sha256,
        }
        if (
            not receipt.promotable
            or receipt.pair_id != pair_id
            or any(
                previous.get(key) is not None and previous[key] != value
                for key, value in expected.items()
            )
        ):
            raise PreviousPairUnavailable(
                "The previous certificate and ledger name different pairs."
            )
        reference = {
            "repo_id": pair.data.repo_id,
            "repo_type": pair.data.repo_type,
            "path": pair.data.dataset_path,
            "revision": pair.data.dataset_revision,
            "sha256": pair.data.dataset_sha256,
        }
        recorded_reference = previous.get("dataset_reference")
        if recorded_reference and any(
            recorded_reference.get(key) != value for key, value in reference.items()
        ):
            raise PreviousPairUnavailable(
                "The previous dataset reference differs from its ledger pair."
            )
        pins.update(
            expected,
            dataset_reference=reference,
            dataset_name=pair.data.dataset,
            release_manifest_reference={
                "repo_id": pair.data.repo_id,
                "repo_type": pair.data.repo_type,
                "path": pair.data.release_manifest_path,
                "revision": pair.data.release_manifest_revision,
                "sha256": pair.data.release_manifest_sha256,
            },
        )
    for key in (
        "bundle_version",
        "model_version",
        "core_version",
        "data_release_version",
        "dataset_sha256",
    ):
        if not isinstance(pins.get(key), str) or not pins[key]:
            raise PreviousPairUnavailable(f"The previous certificate has no {key} pin.")
    reference = pins.get("dataset_reference")
    if (
        not isinstance(reference, Mapping)
        or any(
            not isinstance(reference.get(key), str) or not reference[key]
            for key in ("repo_id", "path", "revision")
        )
        or reference.get("repo_type") not in ("model", "dataset")
        or reference.get("sha256") != pins["dataset_sha256"]
        or not re.fullmatch(r"[a-f0-9]{64}", pins["dataset_sha256"])
    ):
        raise PreviousPairUnavailable(
            "The previous certificate has no exact dataset reference."
        )
    return pins


# This verification subprocess uses the current verifier, independently of
# whether the older published wrapper included it. Its namespace is isolated
# from the later metrics subprocess, which uses the installed previous wrapper.
PREVIOUS_IDENTITY_RUNNER = """
import importlib.metadata as metadata, json, sys, types
from pathlib import Path
settings, out = json.loads(sys.argv[1]), Path(sys.argv[2])
package = types.ModuleType("policyengine")
package.__path__ = [settings["source"]]
sys.modules["policyengine"] = package
from policyengine.provenance.wheels import verify_installed_against_wheel
problems = []
for wheel in settings["wheels"]:
    name = wheel["name"]
    try:
        if metadata.version(name) != wheel["version"]:
            problems.append(name + ": installed version differs from the previous certificate")
        evidence = verify_installed_against_wheel(name, Path(wheel["path"]))
        if evidence["wheel_sha256"] != wheel["sha256"]:
            problems.append(name + ": wheel hash differs from the previous certificate")
        problems.extend(evidence["problems"])
    except (metadata.PackageNotFoundError, OSError, ValueError) as exc:
        problems.append(name + ": cannot verify installation: " + str(exc))
out.write_text(json.dumps({"problems": problems}))
"""


def _construct_previous_pair_python(
    previous: Mapping[str, Any],
    work_dir: Path,
    *,
    ledger_root: Optional[Path] = None,
    run: Optional[Callable[..., Any]] = None,
) -> str:
    """Install and verify the certificate's wheels, independently of wrapper extras."""

    import subprocess

    import requests

    from policyengine.provenance.uk_qualification import _wheel

    run = run if run is not None else subprocess.run
    pins = _previous_pair_pins(previous, ledger_root)
    wheels = []
    for name, kind in (("policyengine-uk", "model"), ("policyengine-core", "core")):
        version = pins[f"{kind}_version"]
        response = requests.get(
            f"https://pypi.org/pypi/{name}/{version}/json", timeout=30
        )
        response.raise_for_status()
        wheel = _wheel(response.json()["urls"], name, version)
        expected_sha256 = pins.get(f"{kind}_wheel_sha256") or wheel.sha256
        if wheel.sha256 != expected_sha256:
            raise PreviousPairUnavailable(
                f"{name}: PyPI wheel differs from the previous certificate."
            )
        path = _download(
            wheel.url,
            work_dir / "previous-wheels" / expected_sha256 / wheel.filename,
            get=requests.get,
        )
        if sha256_file(path) != expected_sha256:
            raise PreviousPairUnavailable(
                f"{name}: downloaded wheel differs from the previous certificate."
            )
        wheels.append(
            {
                "name": name,
                "version": version,
                "sha256": expected_sha256,
                "path": str(path),
            }
        )
    # Same wrapper version can certify several pairs during its publication window.
    # The environment cache must include the resolved wheel and dataset pins.
    venv = (
        work_dir / f"previous-{content_sha256({'pins': pins, 'wheels': wheels})[:24]}"
    )
    python = venv / "bin" / "python"
    if not python.exists():
        run(["uv", "venv", str(venv), "--python", "3.13"], check=True)
        run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                f"policyengine=={pins['bundle_version']}",
                *(wheel["path"] for wheel in wheels),
            ],
            check=True,
        )
    output = work_dir / "previous-identity.json"
    output.unlink(missing_ok=True)
    run(
        [
            str(python),
            "-c",
            PREVIOUS_IDENTITY_RUNNER,
            json.dumps(
                {
                    "source": str(Path(__file__).resolve().parents[1]),
                    "wheels": wheels,
                }
            ),
            str(output),
        ],
        check=True,
    )
    identity = json.loads(output.read_text())
    if not isinstance(identity, Mapping) or identity.get("problems") != []:
        raise PreviousPairUnavailable(
            f"The installed previous pair does not match its pins: {identity}."
        )
    return str(python)


def _materialize_previous_pair_dataset(
    previous: Mapping[str, Any], work_dir: Path, *, ledger_root: Optional[Path] = None
) -> Path:
    """Materialize the previous certificate's exact data, bypassing wrapper defaults."""

    import os

    import requests

    pins = _previous_pair_pins(previous, ledger_root)
    reference = pins["dataset_reference"]
    path = (
        work_dir
        / "previous-data"
        / pins["dataset_sha256"]
        / Path(reference["path"]).name
    )
    if not path.exists():
        token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
        url = _hf_url(
            reference["repo_id"],
            reference["repo_type"],
            reference["revision"],
            reference["path"],
        )
        _download(
            url,
            path,
            get=lambda *args, **kwargs: requests.get(
                *args,
                **kwargs,
                headers={"Authorization": f"Bearer {token}"} if token else {},
            ),
        )
    if sha256_file(path) != pins["dataset_sha256"]:
        raise PreviousPairUnavailable(
            "The previous dataset bytes differ from the certificate."
        )
    manifest_reference = pins.get("release_manifest_reference") or {}
    if (
        any(
            not isinstance(manifest_reference.get(key), str)
            or not manifest_reference[key]
            for key in ("repo_id", "path", "revision")
        )
        or manifest_reference.get("repo_type") not in ("model", "dataset")
        or not pins.get("dataset_name")
    ):
        raise PreviousPairUnavailable(
            "The previous data release has no pinned manifest reference."
        )
    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
    response = requests.get(
        _hf_url(
            manifest_reference["repo_id"],
            manifest_reference["repo_type"],
            manifest_reference["revision"],
            manifest_reference["path"],
        ),
        headers={"Authorization": f"Bearer {token}"} if token else {},
        timeout=30,
    )
    response.raise_for_status()
    if (
        manifest_reference.get("sha256")
        and hashlib.sha256(response.content).hexdigest() != manifest_reference["sha256"]
    ):
        raise PreviousPairUnavailable(
            "The previous release manifest bytes differ from the ledger."
        )
    manifest = DataReleaseManifest.model_validate_json(response.content)
    artifact = manifest.artifacts.get(pins["dataset_name"])
    if (
        manifest.data_package.version != pins["data_release_version"]
        or manifest.default_datasets.get("national") != pins["dataset_name"]
        or artifact is None
        or artifact.sha256 != pins["dataset_sha256"]
        or artifact.path != reference["path"]
        or artifact.revision != reference["revision"]
        or artifact.repo_id != reference["repo_id"]
        or (artifact.repo_type or manifest_reference["repo_type"])
        != reference["repo_type"]
    ):
        raise PreviousPairUnavailable(
            "The previous release manifest does not match the certified data pair."
        )
    return path


def previous_pair_python(
    previous: Mapping[str, Any],
    work_dir: Path,
    *,
    ledger_root: Optional[Path] = None,
    run: Optional[Callable[..., Any]] = None,
) -> str:
    """Construct a verified baseline, or report that it is unavailable."""

    import subprocess

    import requests

    try:
        return _construct_previous_pair_python(
            previous, work_dir, ledger_root=ledger_root, run=run
        )
    except PreviousPairUnavailable:
        raise
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
        requests.RequestException,
    ) as exc:
        raise PreviousPairUnavailable(
            f"The exact previous environment could not be verified: {exc}"
        ) from exc


def previous_pair_dataset(
    previous: Mapping[str, Any], work_dir: Path, *, ledger_root: Optional[Path] = None
) -> Path:
    """Materialize verified previous data, or report that it is unavailable."""

    import requests

    try:
        return _materialize_previous_pair_dataset(
            previous, work_dir, ledger_root=ledger_root
        )
    except PreviousPairUnavailable:
        raise
    except (OSError, ValueError, KeyError, TypeError, requests.RequestException) as exc:
        raise PreviousPairUnavailable(
            f"The exact previous data could not be verified: {exc}"
        ) from exc


# --- Orchestration -------------------------------------------------------------


def run_gate(gate_id: str, function: Callable[[], GateOutcome]) -> GateOutcome:
    """Run one gate; an unexpected exception becomes an ``error`` result."""

    try:
        return function()
    except PreviousPairUnavailable as exc:
        return _result(
            gate_id, "unavailable", str(exc), {"previous_pair_unavailable": str(exc)}
        )
    except Exception as exc:
        return _result(
            gate_id,
            "error",
            f"The gate raised {type(exc).__name__}: {exc}",
            {"traceback": traceback.format_exc()},
        )


def run_gates(
    gates: Sequence[tuple[str, Callable[[], GateOutcome]]],
) -> tuple[list[GateResult], dict[str, Evidence]]:
    """Run gates in order; always one result per gate, never fewer."""

    results: list[GateResult] = []
    evidence: dict[str, Evidence] = {}
    for gate_id, function in gates:
        result, item = run_gate(gate_id, function)
        if result.gate_id != gate_id:
            result = result.model_copy(update={"gate_id": gate_id})
        # Orchestration may append source/tool metadata to a gate's evidence.
        # Bind the result to the complete JSON that will actually be stored.
        item = _json_safe(item)
        result = result.model_copy(update={"evidence_sha256": evidence_sha256(item)})
        results.append(result)
        evidence[gate_id] = item
    return results, evidence


def _download(url: str, destination: Path, *, get: Callable[..., Any]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with destination.open("wb") as stream:
            for chunk in response.iter_content(chunk_size=1 << 20):
                stream.write(chunk)
    return destination


def _previous_gate_evidence(
    ledger_root: Optional[Path], previous: Optional[Mapping[str, Any]]
) -> dict[str, Any]:
    """Verified evidence of the exact certified pair and receipt's attempt.

    Legacy certificates can fall back to recomputation. Once a certified
    receipt records cumulative history, unavailable evidence fails closed.
    """

    if not previous:
        return {}
    pair_id = previous.get("qualification_pair_id")
    if not isinstance(pair_id, str) or not re.fullmatch(r"[a-f0-9]{64}", pair_id):
        return {}
    if ledger_root is None:
        raise PreviousPairUnavailable(
            "The previous certified pair's receipt is unavailable; a fresh "
            "registry decision is required."
        )
    receipt_path = ledger_root / "uk" / pair_id / "qualification_receipt.json"
    certified_history_recorded = False
    receipt_loaded = False
    try:
        receipt = QualificationReceipt.model_validate_json(receipt_path.read_text())
        receipt_loaded = True
        pair = receipt.pair
        by_gate = {gate.gate_id: gate for gate in receipt.gates}
        inputs_gate = by_gate.get("budget_inputs")
        certified_history_recorded = (
            inputs_gate is not None and "ever_usable_inputs" in inputs_gate.details
        )
        if not receipt.promotable or receipt.pair_id != pair_id:
            if certified_history_recorded:
                raise PreviousPairUnavailable(
                    "The cumulative input history does not identify the "
                    "previous certified pair; a fresh registry decision is required."
                )
            return {}
        expected = (
            (pair.model.version, previous.get("model_version")),
            (pair.core.version, previous.get("core_version")),
            (pair.data.release_version, previous.get("data_release_version")),
            (pair.data.dataset_sha256, previous.get("dataset_sha256")),
        )
        if any(actual != certified for actual, certified in expected):
            if certified_history_recorded:
                raise PreviousPairUnavailable(
                    "The cumulative input history does not match the "
                    "previous certified pair's pins; a fresh registry decision "
                    "is required."
                )
            return {}
        # The pair ID binds all wheels and data pins even for certificates
        # whose bundle's package record does not repeat the core wheel hash.
        for field, actual in (
            ("model_wheel_sha256", pair.model.wheel_sha256),
            ("core_wheel_sha256", pair.core.wheel_sha256),
        ):
            if previous.get(field) is not None and previous[field] != actual:
                if certified_history_recorded:
                    raise PreviousPairUnavailable(
                        "The cumulative input history does not match the "
                        "previous certified pair's wheel pins; a fresh registry "
                        "decision is required."
                    )
                return {}
        for attempt_receipt in sorted(
            (receipt_path.parent / "attempts").glob("*/qualification_receipt.json")
        ):
            attempt = QualificationReceipt.model_validate_json(
                attempt_receipt.read_text()
            )
            # Review acceptance can change the latest receipt without changing
            # the immutable attempt's underlying qualification.
            if attempt.unreviewed_sha256 != receipt.unreviewed_sha256:
                continue
            harness = json.loads((attempt_receipt.parent / "harness.json").read_text())
            if harness != receipt.harness.canonical_payload():
                continue
            found = {
                name: json.loads(
                    (attempt_receipt.parent / "gates" / f"{name}.json").read_text()
                )
                for name in ("budget_inputs", "supported_years")
            }
            has_history = (
                certified_history_recorded
                or "ever_usable_inputs" in found["budget_inputs"]
            )
            for name in ("supported_years", "budget_inputs"):
                gate = by_gate.get(name)
                evidence = found[name]
                if (
                    not gate
                    or gate.status not in ("pass", "needs_review")
                    or gate.evidence_sha256 != evidence_sha256(evidence)
                ):
                    if has_history:
                        raise PreviousPairUnavailable(
                            "The previous certified pair's cumulative input "
                            "history could not be verified; a fresh registry "
                            "decision is required."
                        )
                    return {}
            if certified_history_recorded and (
                found["budget_inputs"].get("ever_usable_inputs")
                != inputs_gate.details["ever_usable_inputs"]
            ):
                raise PreviousPairUnavailable(
                    "The previous certified pair's cumulative input history "
                    "does not match its receipt; a fresh registry decision "
                    "is required."
                )
            if has_history and (
                found["budget_inputs"].get("pair_id") != pair_id
                or found["budget_inputs"].get("attempt_id")
                != f"{pair_id}/{attempt_receipt.parent.name}"
            ):
                raise PreviousPairUnavailable(
                    "The previous certified pair's cumulative input history "
                    "belongs to another pair or attempt; a fresh registry "
                    "decision is required."
                )
            if _valid_previous_snapshot_evidence(found):
                return found
            if "ever_usable_inputs" in found["budget_inputs"]:
                # A certified cumulative history cannot be replaced by a
                # fresh direct-predecessor seed when its evidence is damaged.
                raise PreviousPairUnavailable(
                    "The previous certified pair's cumulative input history "
                    "is inconsistent; a fresh registry decision is required."
                )
            return {}
    except PreviousPairUnavailable:
        raise
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        if certified_history_recorded or not receipt_loaded:
            raise PreviousPairUnavailable(
                "The previous certified pair's cumulative input history "
                "could not be read; a fresh registry decision is required."
            ) from exc
        # An unavailable cache is not qualification evidence; recompute it.
        return {}
    if certified_history_recorded:
        raise PreviousPairUnavailable(
            "The previous certified pair's cumulative input history has no "
            "matching attempt; a fresh registry decision is required."
        )
    return {}


def _valid_previous_snapshot_evidence(evidence: Mapping[str, Any]) -> bool:
    years = evidence["supported_years"].get("supported_years")
    inputs = evidence["budget_inputs"]
    missing = inputs.get("missing_inputs")
    unusable = inputs.get("unusable_critical")
    input_status = inputs.get("input_status")
    ever_usable = inputs.get("ever_usable_inputs")
    return (
        isinstance(years, list)
        and bool(years)
        and all(
            isinstance(year, int) and not isinstance(year, bool) and year > 0
            for year in years
        )
        and len(years) == len(set(years))
        and isinstance(missing, list)
        and all(isinstance(name, str) and bool(name) for name in missing)
        and len(missing) == len(set(missing))
        and isinstance(unusable, list)
        and all(
            isinstance(row, list)
            and len(row) == 2
            and all(isinstance(value, str) and bool(value) for value in row)
            for row in unusable
        )
        and (
            "ever_usable_inputs" not in inputs
            or (
                isinstance(ever_usable, list)
                and all(isinstance(name, str) and bool(name) for name in ever_usable)
                and len(ever_usable) == len(set(ever_usable))
                and isinstance(input_status, dict)
                and {
                    name
                    for name, state in input_status.items()
                    if isinstance(state, dict) and state.get("usable") is True
                }.issubset(ever_usable)
            )
        )
        and (
            input_status is None
            or (
                isinstance(input_status, dict)
                and all(
                    isinstance(name, str)
                    and bool(name)
                    and isinstance(state, dict)
                    and all(
                        type(state.get(key)) is bool
                        for key in ("in_model", "in_data", "usable", "is_input")
                    )
                    and (
                        not state["usable"] or (state["in_model"] and state["in_data"])
                    )
                    and (not state["is_input"] or state["in_model"])
                    for name, state in input_status.items()
                )
                and all(
                    type(inputs.get(key)) is int
                    for key in (
                        "model_variables",
                        "model_input_variables",
                        "dataset_columns",
                    )
                )
                and inputs["model_variables"]
                == sum(state["in_model"] for state in input_status.values())
                and inputs["model_input_variables"]
                == sum(state["is_input"] for state in input_status.values())
                and inputs["dataset_columns"]
                == sum(state["in_data"] for state in input_status.values())
                and set(missing)
                == {
                    name
                    for name, state in input_status.items()
                    if state["is_input"] and not state["in_data"]
                }
            )
        )
    )


def run_candidate_gates(
    resolved: Any,
    harness: QualificationHarness,
    *,
    config: Mapping[str, Any],
    work_dir: Path,
    previous_certificate: Optional[Mapping[str, Any]],
    ledger_root: Optional[Path],
) -> tuple[list[GateResult], dict[str, Evidence]]:
    """Run gates 1–9 on the installed candidate, with real I/O."""

    import os

    import requests

    from policyengine.provenance.dataset_materialization import materialize_dataset

    pair: CandidatePair = resolved.pair
    work_dir.mkdir(parents=True, exist_ok=True)
    data_dir = Path(config.get("data_dir") or work_dir / "data")
    qualification_dir = Path(__file__).resolve().parents[1] / "data" / "qualification"
    previous_evidence = _previous_gate_evidence(ledger_root, previous_certificate)
    critical_spec = json.loads(
        (qualification_dir / config["budget_inputs"]["critical"]).read_text()
    )
    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
    state: dict[str, Any] = {}

    def dataset() -> Path:
        if "dataset" not in state:
            source = materialize_dataset("uk", data_dir=data_dir)
            state["dataset"] = Path(source.path)
        path: Path = state["dataset"]
        return path

    def gate_wheels() -> GateOutcome:
        paths = {}
        for package, wheel in (
            (pair.model, resolved.model_wheel),
            (pair.core, resolved.core_wheel),
        ):
            paths[package.name] = _download(
                wheel.url, work_dir / "wheels" / wheel.filename, get=requests.get
            )
        return wheel_hashes(
            pair,
            wheel_paths=paths,
            pypi_digests={
                pair.model.name: resolved.model_wheel.sha256,
                pair.core.name: resolved.core_wheel.sha256,
            },
        )

    def gate_core() -> GateOutcome:
        if "manifest" not in state:
            return _result(
                "core_compatibility",
                "error",
                "The release manifest was not read (data_access did not succeed).",
                {},
            )
        return core_compatibility(
            pair, state["manifest"], model_requires_core=resolved.model_requires_core
        )

    def gate_data_access() -> GateOutcome:
        result, evidence, manifest = data_access(
            pair, get=requests.get, head=requests.head, token=token
        )
        if manifest is not None:
            state["manifest"] = manifest
        return result, evidence

    def previous_environment() -> tuple[str, Path]:
        if "previous_environment" not in state:
            assert previous_certificate is not None
            pins = _previous_pair_pins(previous_certificate, ledger_root)
            state["previous_environment"] = (
                previous_pair_python(pins, work_dir),
                previous_pair_dataset(pins, work_dir),
            )
        return state["previous_environment"]

    def previous_snapshot() -> Optional[dict[str, Any]]:
        """The previous pair's inputs and years: from the ledger, else computed."""

        if "previous_snapshot" in state:
            cached: Optional[dict[str, Any]] = state["previous_snapshot"]
            return cached
        snapshot: Optional[dict[str, Any]] = None
        recorded_inputs = previous_evidence.get("budget_inputs")
        recorded_years = previous_evidence.get("supported_years")
        if (
            recorded_inputs
            and recorded_years
            and isinstance(recorded_inputs.get("input_status"), dict)
            and "ever_usable_inputs" in recorded_inputs
        ):
            snapshot = {
                "missing_inputs": recorded_inputs.get("missing_inputs"),
                "unusable_critical": recorded_inputs.get("unusable_critical", []),
                "supported_years": recorded_years.get("supported_years"),
                "source": "ledger",
                "input_status": recorded_inputs["input_status"],
                "ever_usable_inputs": recorded_inputs["ever_usable_inputs"],
            }
        elif previous_certificate:
            previous_python, previous_dataset = previous_environment()
            snapshot = run_inputs_snapshot(
                previous_python,
                critical=critical_spec["critical"],
                out=work_dir / "previous-inputs.json",
                dataset_path=previous_dataset,
            )
            snapshot["source"] = (
                f"computed with policyengine {previous_certificate['bundle_version']}"
            )
        state["previous_snapshot"] = snapshot
        return snapshot

    def gate_years() -> GateOutcome:
        previous = previous_snapshot()
        previous_years = previous.get("supported_years") if previous else None
        return supported_years(
            pair,
            dataset(),
            required_years=config["required_years"],
            budget_horizon_years=config["budget_horizon_years"],
            previous_supported_years=previous_years,
        )

    def gate_inputs() -> GateOutcome:
        from policyengine_uk.system import system

        previous = previous_snapshot()
        input_names = [
            name
            for name, variable in system.variables.items()
            if variable.is_input_variable()
        ]
        previous_status = previous.get("input_status") if previous else None
        if isinstance(previous_status, dict):
            # Do not project away variables removed or made formula-backed by
            # the candidate: they may already have expired an exception.
            previous_status = dict(previous_status)
            for name in system.variables:
                previous_status.setdefault(
                    name,
                    {
                        "in_model": False,
                        "is_input": False,
                        "in_data": False,
                        "usable": False,
                    },
                )
        result, evidence = budget_inputs(
            pair,
            dataset(),
            model_input_variables=input_names,
            model_variables=system.variables,
            critical_inputs=critical_spec["critical"],
            accepted_gaps=critical_spec.get("accepted_gaps", {}),
            previous_missing_inputs=previous.get("missing_inputs")
            if previous
            else None,
            previous_unusable_critical=(
                [item[0] for item in previous.get("unusable_critical", [])]
                if previous
                else None
            ),
            previous_input_status=previous_status,
            previous_ever_usable_inputs=previous.get("ever_usable_inputs")
            if previous
            else None,
        )
        evidence["previous_source"] = previous.get("source") if previous else None
        return result, evidence

    def gate_contract() -> GateOutcome:
        settings = config["reform_contract"]
        return reform_contract(
            entrypoint=settings.get("entrypoint"),
            dataset_path=dataset(),
            seed=int(settings.get("seed", 0)),
            max_examples=int(settings.get("max_examples", 50)),
            expected_versions={
                pair.model.name: pair.model.version,
                pair.core.name: pair.core.version,
            },
            expected_dataset_sha256=pair.data.dataset_sha256,
            pending_decisions=settings.get("pending_decisions", ()),
        )

    def metrics_tool() -> Path:
        if "metrics_tool" not in state:
            state["metrics_tool"] = vendor_metrics_tool(
                config["metrics"]["tool"], work_dir, get=requests.get
            )
        tool_root: Path = state["metrics_tool"]
        return tool_root

    def standard_reforms() -> list[dict[str, Any]]:
        if "standard_reforms" not in state:
            state["standard_reforms"] = load_standard_reforms(
                metrics_tool(),
                config["reform_responsiveness"]["standard_reforms_file"],
            )
        reforms: list[dict[str, Any]] = state["standard_reforms"]
        return reforms

    def candidate_metrics() -> dict[str, Any]:
        """The candidate's report, computed once for both metric gates."""

        import sys

        if "candidate_metrics" not in state:
            state["candidate_metrics"] = run_metrics_report(
                sys.executable,
                metrics_tool(),
                years=config["metrics"]["years"],
                out=work_dir / "metrics-candidate.json",
                dataset_path=dataset(),
                label="candidate",
            )
            state.setdefault("metrics_reports", {})["candidate"] = state[
                "candidate_metrics"
            ]
        report: dict[str, Any] = state["candidate_metrics"]
        return report

    def gate_responsiveness() -> GateOutcome:
        settings = config.get("reform_responsiveness")
        if not settings or not config["metrics"].get("tool"):
            return reform_responsiveness(
                report=None,
                standard_reforms=[],
                years=[],
                unavailable_reason=(
                    "No reform responsiveness settings or metrics tool is configured."
                ),
            )
        result, evidence = reform_responsiveness(
            report=candidate_metrics(),
            standard_reforms=standard_reforms(),
            years=config["metrics"]["years"],
        )
        evidence["tool"] = dict(config["metrics"]["tool"])
        return result, evidence

    def gate_metrics() -> GateOutcome:
        import sys

        settings = config["metrics"]
        tool = settings.get("tool")
        if not tool:
            return metrics_review(
                candidate_report=None,
                previous_report=None,
                bounds={},
                unavailable_reason="No metrics tool commit is configured (metrics.tool).",
            )
        if not previous_certificate:
            return metrics_review(
                candidate_report=None,
                previous_report=None,
                bounds={},
                unavailable_reason="No previous certificate to compare against.",
            )
        bounds = json.loads((qualification_dir / settings["bounds"]).read_text())
        previous_python, previous_dataset = previous_environment()
        vendor_root = metrics_tool()
        years = settings["years"]
        candidate_report = candidate_metrics()
        previous_report = run_metrics_report(
            previous_python,
            vendor_root,
            years=years,
            out=work_dir / "metrics-previous.json",
            dataset_path=previous_dataset,
            label="previous",
        )
        cross_report = None
        if previous_certificate.get("dataset_sha256") != pair.data.dataset_sha256:
            cross_report = run_metrics_report(
                sys.executable,
                vendor_root,
                years=years,
                out=work_dir / "metrics-candidate-model-previous-data.json",
                dataset_path=Path(previous_report["dataset_path"]),
                label="candidate model, previous data",
            )
        state.setdefault("metrics_reports", {}).update(
            previous=previous_report,
            candidate_model_previous_data=cross_report,
        )
        result, evidence = metrics_review(
            candidate_report=candidate_report,
            previous_report=previous_report,
            bounds=bounds,
            cross_report=cross_report,
        )
        evidence["tool"] = dict(tool)
        evidence["partition_sources"] = {
            "candidate": candidate_report.get("partition_source"),
            "previous": previous_report.get("partition_source"),
        }
        return result, evidence

    gates = [
        ("installed_versions", lambda: installed_versions(pair, harness)),
        ("wheel_hashes", gate_wheels),
        ("data_access", gate_data_access),
        ("core_compatibility", gate_core),
        ("dataset_bytes", lambda: dataset_bytes(pair, dataset())),
        ("supported_years", gate_years),
        ("budget_inputs", gate_inputs),
        ("reform_contract", gate_contract),
        ("metrics_review", gate_metrics),
        ("reform_responsiveness", gate_responsiveness),
    ]
    results, evidence = run_gates(gates)
    for name, report in (state.get("metrics_reports") or {}).items():
        if report is not None:
            evidence[f"metrics_report_{name}"] = publishable_metrics_report(report)
    return results, evidence


def version_sort_key(version: str) -> Version:
    return Version(version)
