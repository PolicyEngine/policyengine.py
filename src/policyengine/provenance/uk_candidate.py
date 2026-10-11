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
import io
import json
import math
import traceback
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
    """Evidence as strict JSON: non-finite numbers become their names."""

    if isinstance(value, float) and not math.isfinite(value):
        return (
            "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
        )
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
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
    tables: Optional[Mapping[str, Any]] = None,
) -> GateOutcome:
    """Critical inputs are present and usable; no input goes newly missing."""

    tables = dict(tables) if tables is not None else dataset_columns(dataset_path)
    columns: dict[str, str] = {}
    for entity, table in tables.items():
        for column in table.columns:
            columns.setdefault(column, entity)
    inputs = set(model_input_variables)
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
    evidence = {
        "model_input_variables": len(inputs),
        "dataset_columns": len(columns),
        "missing_inputs": missing,
        "newly_missing_inputs": newly_missing,
        "unusable_critical": [list(item) for item in unusable],
        "accepted_gaps": dict(accepted_gaps),
    }
    details = {
        "missing_inputs": len(missing),
        "newly_missing_inputs": newly_missing,
        "unusable_critical": [name for name, _ in unusable],
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
) -> Callable[..., Any]:
    module_name, _, attribute = entrypoint.partition(":")
    if not attribute:
        module_name, _, attribute = entrypoint.rpartition(".")
    module = importer(module_name)
    function: Callable[..., Any] = getattr(module, attribute)
    return function


#: Report sections: the key that names each row, and what a row is called.
_CONTRACT_SECTIONS = (
    ("cases", "case_id", "case"),
    ("properties", "property_id", "property"),
    ("population", "check_id", "population check"),
)
_CONTRACT_STATUSES = ("pass", "fail", "error", "unsupported", "pending")


def reform_contract(
    *,
    entrypoint: Optional[str],
    dataset_path: Optional[Path],
    seed: int,
    max_examples: int,
    expected_versions: Optional[Mapping[str, str]] = None,
    expected_dataset_sha256: Optional[str] = None,
    importer: Callable[[str], Any] = importlib.import_module,
) -> GateOutcome:
    """Run the Budget reform contract (W1) on every route and gate on its report.

    ``fail`` when any case, sampled property or population check fails or
    errors. ``error`` when the report cannot be trusted as a full run of this
    candidate:
    - a pending row lacks its ``decision_id``, or an unsupported case or
      population check lacks its ``reason``;
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
        runner = _load_entrypoint(entrypoint, importer)
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
                if not row.get("decision_id"):
                    malformed.append(f"{label} is pending without a decision_id")
                pending.append(label)
            elif status == "unsupported":
                if section == "properties":
                    malformed.append(
                        f"{label} did not run: {row.get('reason') or 'no reason given'}"
                    )
                elif not row.get("reason"):
                    malformed.append(f"{label} is unsupported without a reason")
                unsupported.append(label)
            elif status != "pass":
                malformed.append(f"{label} has unknown status {status!r}")
    if not report.get("cases"):
        malformed.append("the report has no cases")
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
    details = {
        "contract_id": report.get("contract_id"),
        "contract_version": report.get("contract_version"),
        "report_sha256": evidence_sha256(report),
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
            report,
            details,
        )
    if malformed:
        return _result(
            "reform_contract", "error", "; ".join(malformed[:8]), report, details
        )
    return _result(
        "reform_contract",
        "pass",
        f"Contract {details['contract_version']}: every case, property and "
        f"population check passed ({counts['pass']})"
        + (f"; {len(pending)} pending a methodology call" if pending else "")
        + (f"; {len(unsupported)} unsupported by design" if unsupported else "")
        + ".",
        report,
        details,
    )


# --- 9. Metrics review ---------------------------------------------------------


def _metric_key(row: Mapping[str, Any]) -> tuple[str, Optional[int]]:
    return (str(row["metric_id"]), row.get("year"))


def _bound(bounds: Mapping[str, Any], kind: Optional[str]) -> tuple[float, float]:
    spec = (bounds.get("kinds") or {}).get(kind) or bounds.get("default") or {}
    return float(spec.get("relative", 0.0)), float(spec.get("absolute", 0.0))


#: Metric-report check prefixes (``identities[].identity_id``) that fail a
#: candidate whatever the previous pair did: none fail on main.
HARD_CHECK_PREFIXES = ("finite:", "weights:", "closure", "identity:", "determinism:")
#: Checks that already fail on main for known model defects (for example
#: ``counted_once:statutory_sick_pay``): they fail a candidate only when the
#: previous certified pair passed them.
REGRESSION_CHECK_PREFIXES = (
    "counted_once:",
    "double_count_present:",
    "sign:",
    "bounds:",
    "reform_runs:",
)


def classify_check(identity_id: str) -> str:
    """``hard``, ``regression`` or ``hard`` for an unknown check (no skips)."""

    if identity_id.startswith(REGRESSION_CHECK_PREFIXES):
        return "regression"
    return "hard"


def compare_metric_reports(
    candidate: Mapping[str, Any],
    previous: Mapping[str, Any],
    bounds: Mapping[str, Any],
) -> tuple[str, str, Evidence]:
    """``(status, summary, evidence)`` for a candidate against a previous report.

    Checks (``identities``) follow the metric tool's classification: hard
    checks fail outright; known-defect checks fail only as regressions from
    the previous pair; ``warn`` is recorded, and a check that newly warns
    where the previous pair passed needs review.
    """

    problems: list[str] = []
    review: list[str] = []
    if candidate.get("status") not in (None, "ok"):
        problems.append(f"the candidate report status is {candidate.get('status')!r}")
    previous_checks = {
        str(row.get("identity_id")): row.get("status")
        for row in previous.get("identities", [])
    }
    hard_failures, regressions, preexisting, new_warnings, warnings_ = (
        [],
        [],
        [],
        [],
        [],
    )
    for row in candidate.get("identities", []):
        check_id = str(row.get("identity_id"))
        status = row.get("status")
        before = previous_checks.get(check_id)
        if status == "fail":
            if classify_check(check_id) == "hard":
                hard_failures.append(check_id)
            elif before == "pass" or before is None:
                regressions.append(check_id)
            else:
                preexisting.append(check_id)
        elif status == "warn":
            warnings_.append(check_id)
            if before == "pass":
                new_warnings.append(check_id)
    if hard_failures:
        problems.append(f"checks failed: {', '.join(hard_failures[:8])}")
    if regressions:
        problems.append(
            f"checks the previous pair passed now fail: {', '.join(regressions[:8])}"
        )
    if new_warnings:
        review.append(f"checks newly warn: {', '.join(new_warnings[:8])}")
    if candidate.get("metrics_version") != previous.get("metrics_version"):
        problems.append(
            "metric definitions differ between the reports "
            f"({previous.get('metrics_version')} → {candidate.get('metrics_version')})"
        )
    if candidate.get("partition_version") != previous.get("partition_version"):
        review.append("the model's fiscal partition changed")
    current = {_metric_key(row): row for row in candidate.get("metrics", [])}
    before_metrics = {_metric_key(row): row for row in previous.get("metrics", [])}
    nonfinite = [
        f"{key[0]} {key[1]}"
        for key, row in current.items()
        if row.get("value") is None
        or not isinstance(row.get("value"), (int, float))
        or not math.isfinite(float(row["value"]))
    ]
    if nonfinite:
        problems.append(f"non-finite values: {', '.join(nonfinite[:8])}")
    lost = sorted(f"{key[0]} {key[1]}" for key in set(before_metrics) - set(current))
    if lost:
        problems.append(f"metrics disappeared: {', '.join(lost[:8])}")
    moves = []
    for key, row in sorted(
        current.items(), key=lambda item: (item[0][0], item[0][1] or 0)
    ):
        old = before_metrics.get(key)
        if old is None:
            continue
        try:
            new_value, old_value = float(row["value"]), float(old["value"])
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(new_value) and math.isfinite(old_value)):
            continue
        relative, absolute = _bound(bounds, row.get("kind"))
        threshold = max(relative * abs(old_value), absolute)
        change = new_value - old_value
        if abs(change) > threshold:
            moves.append(
                {
                    "metric_id": key[0],
                    "year": key[1],
                    "kind": row.get("kind"),
                    "previous": old_value,
                    "candidate": new_value,
                    "change": change,
                    "threshold": threshold,
                }
            )
    if moves:
        review.append(f"{len(moves)} metric move(s) exceed their review bounds")
    evidence = {
        "metrics_version": candidate.get("metrics_version"),
        "partition_version": candidate.get("partition_version"),
        "previous_partition_version": previous.get("partition_version"),
        "hard_check_failures": hard_failures,
        "regressed_checks": regressions,
        "preexisting_check_failures": preexisting,
        "warn_identities": warnings_,
        "new_warnings": new_warnings,
        "moves_beyond_bounds": moves,
        "candidate_report_sha256": evidence_sha256(candidate),
        "previous_report_sha256": evidence_sha256(previous),
    }
    if problems:
        return "fail", "; ".join(problems), evidence
    if review:
        return "needs_review", "; ".join(review), evidence
    note = (
        f" ({len(preexisting)} known check failures carried over)"
        if preexisting
        else ""
    )
    return "pass", f"{len(current)} metrics within their review bounds{note}.", evidence


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


# --- Reform responsiveness -------------------------------------------------------


def _fiscal_year(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def reform_responsiveness(
    *,
    report: Optional[Mapping[str, Any]],
    standard_reforms: Sequence[Mapping[str, Any]],
    years: Sequence[int],
    reference_year: int,
    floor_gbp: float,
    min_share_of_expected: float,
    unavailable_reason: Optional[str] = None,
) -> GateOutcome:
    """Every standard reform moves the government balance as expected, or fail.

    ``report`` is the candidate's metrics report, whose ``reforms.<id>``
    metrics are each reform's change in weighted ``gov_balance`` from a full
    run. A standard reform passes when all of these hold:

    - it ran (``reform_runs:<id>`` passed) and has a finite value in every
      year of ``years``;
    - in every year the change has the sign of its ``expected_impact`` and is
      at least ``floor_gbp`` in size;
    - in ``reference_year`` it is at least ``min_share_of_expected`` of
      ``|expected_impact|`` (given in GBP bn).

    Any failure fails the gate: a reform that silently does nothing is a
    defect, never a small number to review. The gate is monotone in each
    reform's response: shrinking a value toward zero or flipping its sign
    never turns a failure into a pass.
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
            "No standard reform set is configured.",
            {},
        )
    if reference_year not in years:
        return _result(
            "reform_responsiveness",
            "error",
            f"The reference year {reference_year} is outside the measured years.",
            {},
        )
    ids: Mapping[str, str] = report.get("reform_ids") or {}
    checks = {
        str(row.get("identity_id")): row.get("status")
        for row in report.get("identities") or []
    }
    values = {
        (str(row.get("metric_id")), row.get("year")): row.get("value")
        for row in report.get("metrics") or []
    }
    problems: list[str] = []
    configuration: list[str] = []
    table: list[dict[str, Any]] = []
    for reform in standard_reforms:
        name = str(reform.get("name"))
        expected = reform.get("expected_impact")
        if (
            isinstance(expected, bool)
            or not isinstance(expected, (int, float))
            or not math.isfinite(expected)
            or expected == 0
        ):
            configuration.append(f"{name!r} has no non-zero expected_impact")
            continue
        direction = 1.0 if expected > 0 else -1.0
        row: dict[str, Any] = {
            "name": name,
            "expected_impact_bn": float(expected),
            "values": {},
            "problems": [],
        }
        table.append(row)
        reform_id = ids.get(name)
        if reform_id is None:
            row["problems"].append("was not run")
        elif checks.get(f"reform_runs:{reform_id}") != "pass":
            row["problems"].append("did not run to completion")
        else:
            for year in years:
                value = values.get((f"reforms.{reform_id}", year))
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                ):
                    row["problems"].append(f"has no costing for {_fiscal_year(year)}")
                    continue
                row["values"][str(year)] = float(value)
                if value * direction <= 0:
                    row["problems"].append(
                        f"moved the balance by £{value:,.0f} in {_fiscal_year(year)}; "
                        f"expected a {'gain' if direction > 0 else 'cost'}"
                    )
                elif abs(value) < floor_gbp:
                    row["problems"].append(
                        f"moved the balance by only £{value:,.0f} in "
                        f"{_fiscal_year(year)} (floor £{floor_gbp:,.0f})"
                    )
                elif (
                    year == reference_year
                    and abs(value) < min_share_of_expected * abs(expected) * 1e9
                ):
                    row["problems"].append(
                        f"moved the balance by £{value / 1e9:,.2f}bn in "
                        f"{_fiscal_year(year)}, under {min_share_of_expected:.0%} of "
                        f"the expected £{expected:,.1f}bn"
                    )
        problems.extend(f"{name}: {problem}" for problem in row["problems"])
    evidence = {
        "reference_year": reference_year,
        "floor_gbp": floor_gbp,
        "min_share_of_expected": min_share_of_expected,
        "years": list(years),
        "reforms": table,
        "candidate_report_sha256": evidence_sha256(report),
    }
    if configuration:
        return _result(
            "reform_responsiveness", "error", "; ".join(configuration[:8]), evidence
        )
    if problems:
        return _result(
            "reform_responsiveness",
            "fail",
            f"{len(problems)} responsiveness failure(s): " + "; ".join(problems[:6]),
            evidence,
        )
    return _result(
        "reform_responsiveness",
        "pass",
        f"All {len(table)} standard reforms move the government balance in the "
        f"expected direction in every year from {_fiscal_year(years[0])} to "
        f"{_fiscal_year(years[-1])}.",
        evidence,
    )


# --- Metrics tool (W3's aggregate-impact report) ---------------------------------

VENDORED_TOOL_PACKAGE = "pe_uk_aggregate_impact"
VENDORED_REFORMS_FILE = "reforms_config.yaml"
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
reforms = [
    {"name": reform["name"], "parameters": reform["parameters"]}
    for reform in settings.get("reforms") or []
]
report = api.compute_budget_metrics(
    Microsimulation(dataset=str(dataset)),
    years=settings["years"],
    partition=partition_module.load_partition(partition_path),
    reforms=reforms,
    run_guard=settings.get("run_guard", True),
    label=settings.get("label", "candidate"),
)
report["partition_source"] = source
report["dataset_path"] = str(dataset)
# The tool names each reform's metrics by its own slug of the reform's name.
slug = importlib.import_module("pe_uk_aggregate_impact.measure").slug
report["reform_ids"] = {reform["name"]: slug(reform["name"]) for reform in reforms}
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
if inputs is None:
    from policyengine_uk.system import system
    inputs = [name for name, variable in system.variables.items() if variable.is_input_variable()]
inputs = set(inputs)
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
    "missing_inputs": sorted(inputs - set(columns)),
    "unusable_critical": unusable,
    "supported_years": [y for y in years if y >= first_year],
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
    reforms_path = tool.get("reforms_path")
    root = destination / f"metrics-tool-{commit[:12]}"
    package = root / VENDORED_TOOL_PACKAGE
    if (package / "api.py").exists() and (
        not reforms_path or (root / VENDORED_REFORMS_FILE).exists()
    ):
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
            elif reforms_path and relative == reforms_path:
                target = root / VENDORED_REFORMS_FILE
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
    if reforms_path and not (root / VENDORED_REFORMS_FILE).exists():
        raise ValueError(f"{repository}@{commit} has no {reforms_path}.")
    return root


def load_standard_reforms(
    vendor_root: Optional[Path], settings: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The standard reform set: the tool's own list, then ``additional_reforms``.

    Each entry has ``name``, ``parameters`` and ``expected_impact`` (the
    change in government balance in the reference year, in GBP bn, from a real
    run). Names must be unique, so one reform has one definition.
    """

    reforms: list[dict[str, Any]] = []
    path = vendor_root / VENDORED_REFORMS_FILE if vendor_root is not None else None
    if path is not None and path.exists():
        import yaml  # type: ignore[import-untyped]

        document = yaml.safe_load(path.read_text()) or {}
        reforms.extend(dict(reform) for reform in document.get("reforms") or [])
    reforms.extend(dict(reform) for reform in settings.get("additional_reforms") or [])
    names = [str(reform.get("name")) for reform in reforms]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Standard reforms are defined twice: {duplicates}")
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
    reforms: Sequence[Mapping[str, Any]] = (),
    run: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Compute a metrics report with ``python`` (any environment) via the runner.

    ``reforms`` (``name`` and ``parameters``) are costed against the same
    baseline, each as a full run over ``years``.
    """

    import subprocess

    run = run if run is not None else subprocess.run
    settings = {
        "years": list(years),
        "dataset_path": str(dataset_path) if dataset_path else None,
        "data_dir": str(data_dir) if data_dir else None,
        "run_guard": run_guard,
        "label": label,
        "reforms": [
            {"name": reform["name"], "parameters": reform["parameters"]}
            for reform in reforms
        ],
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


def previous_pair_python(
    previous: Mapping[str, Any],
    work_dir: Path,
    *,
    run: Optional[Callable[..., Any]] = None,
) -> str:
    """A throwaway venv with the previous certified release installed."""

    import subprocess

    run = run if run is not None else subprocess.run
    venv = work_dir / f"previous-{previous['bundle_version']}"
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
                f"policyengine[uk]=={previous['bundle_version']}",
            ],
            check=True,
        )
    return str(python)


# --- Orchestration -------------------------------------------------------------


def run_gate(gate_id: str, function: Callable[[], GateOutcome]) -> GateOutcome:
    """Run one gate; an unexpected exception becomes an ``error`` result."""

    try:
        return function()
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
    """Evidence the previous certificate's qualification recorded, if any."""

    if ledger_root is None or not previous:
        return {}
    base = ledger_root / "uk"
    if not base.is_dir():
        return {}
    for receipt_path in base.glob("*/qualification_receipt.json"):
        receipt = json.loads(receipt_path.read_text())
        pair = receipt.get("pair", {})
        if (
            pair.get("model", {}).get("version") == previous.get("model_version")
            and pair.get("data", {}).get("release_version")
            == previous.get("data_release_version")
            and receipt.get("verdict") in ("qualified", "needs_review")
        ):
            found: dict[str, Any] = {}
            attempts = sorted((receipt_path.parent / "attempts").glob("*/gates"))
            if attempts:
                for name in ("supported_years", "budget_inputs"):
                    path = attempts[-1] / f"{name}.json"
                    if path.exists():
                        found[name] = json.loads(path.read_text())
            return found
    return {}


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

    def previous_snapshot() -> Optional[dict[str, Any]]:
        """The previous pair's inputs and years: from the ledger, else computed."""

        if "previous_snapshot" in state:
            cached: Optional[dict[str, Any]] = state["previous_snapshot"]
            return cached
        snapshot: Optional[dict[str, Any]] = None
        recorded_inputs = previous_evidence.get("budget_inputs")
        recorded_years = previous_evidence.get("supported_years")
        if recorded_inputs and recorded_years:
            snapshot = {
                "missing_inputs": recorded_inputs.get("missing_inputs"),
                "unusable_critical": recorded_inputs.get("unusable_critical", []),
                "supported_years": recorded_years.get("supported_years"),
                "source": "ledger",
            }
        elif previous_certificate:
            snapshot = run_inputs_snapshot(
                previous_pair_python(previous_certificate, work_dir),
                critical=critical_spec["critical"],
                out=work_dir / "previous-inputs.json",
                data_dir=work_dir / "previous-data",
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
        result, evidence = budget_inputs(
            pair,
            dataset(),
            model_input_variables=[
                name
                for name, variable in system.variables.items()
                if variable.is_input_variable()
            ],
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
                metrics_tool(), config.get("reform_responsiveness") or {}
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
                reforms=standard_reforms(),
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
                reference_year=0,
                floor_gbp=0.0,
                min_share_of_expected=0.0,
                unavailable_reason=(
                    "No reform responsiveness settings or metrics tool is configured."
                ),
            )
        result, evidence = reform_responsiveness(
            report=candidate_metrics(),
            standard_reforms=standard_reforms(),
            years=config["metrics"]["years"],
            reference_year=int(settings["reference_year"]),
            floor_gbp=float(settings["floor_gbp"]),
            min_share_of_expected=float(settings["min_share_of_expected"]),
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
        vendor_root = metrics_tool()
        years = settings["years"]
        candidate_report = candidate_metrics()
        previous_report = run_metrics_report(
            previous_pair_python(previous_certificate, work_dir),
            vendor_root,
            years=years,
            out=work_dir / "metrics-previous.json",
            data_dir=work_dir / "previous-data",
            label="previous",
            reforms=standard_reforms(),
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
                reforms=standard_reforms(),
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
            evidence[f"metrics_report_{name}"] = report
    return results, evidence


def version_sort_key(version: str) -> Version:
    return Version(version)
