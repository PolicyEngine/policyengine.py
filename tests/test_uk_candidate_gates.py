"""Mandatory local qualification gates (no network, no credentials).

Invariants:

- installed files match the wheel byte for byte, or the gate fails: mutating
  any single installed file fails it;
- no gate can skip: a missing harness is ``unavailable`` and a crash is
  ``error``; ``run_gates`` returns exactly one result per gate;
- inputs newly missing from the data are exactly (missing now) − (missing
  before); a critical input that becomes unusable always fails;
- metric review is monotone: shrinking every move toward zero never makes
  the status worse.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from policyengine.provenance import uk_candidate as gates_module
from policyengine.provenance.manifest import DataReleaseManifest
from policyengine.provenance.uk_candidate import (
    budget_inputs,
    compare_metric_reports,
    core_compatibility,
    data_access,
    dataset_bytes,
    installed_versions,
    metrics_review,
    reform_contract,
    run_gates,
    supported_years,
    wheel_hashes,
)
from policyengine.provenance.wheels import (
    parse_record,
    record_digest_to_hex,
    verify_installed_against_wheel,
)
from tests.qualification_fixtures import HARNESS, make_pair, make_receipt

# --- Installed versions --------------------------------------------------------


class FakeMetadata:
    PackageNotFoundError = KeyError

    def __init__(self, versions, requires):
        self.versions, self._requires = versions, requires

    def version(self, name):
        return self.versions[name]

    def requires(self, name):
        return self._requires.get(name, [])


def test_installed_versions_pass_and_fail():
    pair = make_pair()
    versions = {
        "policyengine": "6.2.6",
        "policyengine-uk": "2.126.8",
        "policyengine-core": "3.33.0",
        "numpy": "2.1.0",
    }
    requires = {
        "policyengine-uk": ["policyengine-core>=3.32.27", "numpy>=1.26"],
        "policyengine": ["pydantic; extra == 'docs'"],
    }
    result, _ = installed_versions(
        pair, HARNESS, metadata=FakeMetadata(versions, requires)
    )
    assert result.status == "pass", result.summary
    result, evidence = installed_versions(
        pair,
        HARNESS,
        metadata=FakeMetadata({**versions, "policyengine-uk": "2.126.6"}, requires),
    )
    assert result.status == "fail" and "2.126.6" in result.summary
    result, _ = installed_versions(
        pair,
        HARNESS,
        metadata=FakeMetadata({**versions, "policyengine-core": "3.30.0"}, requires),
    )
    assert result.status == "fail"
    result, _ = installed_versions(
        pair,
        HARNESS,
        metadata=FakeMetadata(
            versions, {**requires, "policyengine-core": ["missing-pkg>=1"]}
        ),
    )
    assert result.status == "fail" and "missing-pkg" in result.summary


# --- Wheel RECORD verification ----------------------------------------------------


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")


FILES = {
    "policyengine_uk/__init__.py": b"VERSION = '2.126.8'\n",
    "policyengine_uk/system.py": b"system = object()\n",
    "policyengine_uk/parameters/rate.yaml": b"values:\n  2027-04-06: 0.2\n",
}


def _build(tmp_path: Path, files=FILES):
    dist_info = "policyengine_uk-2.126.8.dist-info"
    record_lines = [
        f"{path},sha256={_b64(data)},{len(data)}" for path, data in files.items()
    ]
    record_lines.append(f"{dist_info}/RECORD,,")
    wheel = tmp_path / "policyengine_uk-2.126.8-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for path, data in files.items():
            archive.writestr(path, data)
        archive.writestr(f"{dist_info}/RECORD", "\n".join(record_lines) + "\n")
    site = tmp_path / "site"
    for path, data in files.items():
        (site / path).parent.mkdir(parents=True, exist_ok=True)
        (site / path).write_bytes(data)
    installed_record = record_lines + [
        f"{dist_info}/INSTALLER,sha256={_b64(b'uv')},2",
        f"{dist_info}/REQUESTED,,",
    ]
    return wheel, site, installed_record


class FakeDistribution:
    def __init__(self, site: Path, record_lines):
        self.site = site
        self.files = []
        for line in record_lines:
            path, digest, *_ = line.split(",")
            hash_ = (
                SimpleNamespace(mode="sha256", value=digest.split("=", 1)[1])
                if digest
                else None
            )
            self.files.append(SimpleNamespace(hash=hash_, __str__=None, path=path))

    def locate_file(self, path):
        return self.site / path


class _File(str):
    pass


def _distribution(site, record_lines):
    dist = SimpleNamespace(site=site, files=[], locate_file=lambda path: site / path)
    for line in record_lines:
        path, digest, *_ = line.split(",")
        item = _File(path)
        item.hash = (
            SimpleNamespace(mode="sha256", value=digest.split("=", 1)[1])
            if digest
            else None
        )
        dist.files.append(item)
    return dist


def _metadata_for(site, record_lines):
    return SimpleNamespace(distribution=lambda name: _distribution(site, record_lines))


def test_record_hash_decoding():
    data = b"hello"
    assert (
        record_digest_to_hex(f"sha256={_b64(data)}") == hashlib.sha256(data).hexdigest()
    )
    parsed = parse_record(f"a.py,sha256={_b64(data)},5\nRECORD,,\n")
    assert parsed == {"a.py": hashlib.sha256(data).hexdigest(), "RECORD": None}
    with pytest.raises(ValueError):
        record_digest_to_hex("md5=abc")


def test_untouched_install_verifies(tmp_path):
    wheel, site, record = _build(tmp_path)
    evidence = verify_installed_against_wheel(
        "policyengine-uk", wheel, metadata=_metadata_for(site, record)
    )
    assert evidence["problems"] == []
    assert evidence["files_verified"] == len(FILES)


@settings(max_examples=30, deadline=None)
@given(index=st.integers(0, len(FILES) - 1), extra=st.binary(min_size=1, max_size=8))
def test_any_mutated_installed_file_fails(tmp_path_factory, index, extra):
    tmp_path = tmp_path_factory.mktemp("wheel")
    wheel, site, record = _build(tmp_path)
    target = site / list(FILES)[index]
    target.write_bytes(target.read_bytes() + extra)
    evidence = verify_installed_against_wheel(
        "policyengine-uk", wheel, metadata=_metadata_for(site, record)
    )
    assert evidence["problems"]


def test_extra_installed_file_fails(tmp_path):
    wheel, site, record = _build(tmp_path)
    (site / "policyengine_uk" / "injected.py").write_bytes(b"x = 1\n")
    record = record + [f"policyengine_uk/injected.py,sha256={_b64(b'x = 1')},6"]
    evidence = verify_installed_against_wheel(
        "policyengine-uk", wheel, metadata=_metadata_for(site, record)
    )
    assert any("injected.py" in problem for problem in evidence["problems"])


def test_wheel_hash_gate(tmp_path):
    wheel, site, record = _build(tmp_path)
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    pair = make_pair()
    pair = pair.model_copy(
        update={"model": pair.model.model_copy(update={"wheel_sha256": digest})}
    )
    (tmp_path / "core").mkdir()
    core_wheel, core_site, core_record = _build(tmp_path / "core")
    core_digest = hashlib.sha256(core_wheel.read_bytes()).hexdigest()
    pair = pair.model_copy(
        update={"core": pair.core.model_copy(update={"wheel_sha256": core_digest})}
    )
    metadata = SimpleNamespace(
        distribution=lambda name: (
            _distribution(site, record)
            if name == "policyengine-uk"
            else _distribution(core_site, core_record)
        )
    )
    result, _ = wheel_hashes(
        pair,
        wheel_paths={"policyengine-uk": wheel, "policyengine-core": core_wheel},
        pypi_digests={"policyengine-uk": digest, "policyengine-core": core_digest},
        metadata=metadata,
    )
    assert result.status == "pass", result.summary
    result, _ = wheel_hashes(
        pair,
        wheel_paths={"policyengine-uk": wheel, "policyengine-core": core_wheel},
        pypi_digests={"policyengine-uk": "0" * 64, "policyengine-core": core_digest},
        metadata=metadata,
    )
    assert result.status == "fail"


# --- Core compatibility, data access, bytes, years -----------------------------------


def _manifest(model_claims=(), core_claims=()):
    return DataReleaseManifest.model_validate(
        {
            "schema_version": 1,
            "data_package": {"name": "policyengine-uk-data", "version": "1.58.0"},
            "compatible_model_packages": [
                {"name": "policyengine-uk", "specifier": s} for s in model_claims
            ],
            "compatible_core_packages": [
                {"name": "policyengine-core", "specifier": s} for s in core_claims
            ],
            "default_datasets": {"national": "enhanced_frs_2024_25"},
            "build": {
                "build_id": "b",
                "built_with_model_package": {
                    "name": "policyengine-uk",
                    "version": "2.122.2",
                },
            },
            "artifacts": {
                "enhanced_frs_2024_25": {
                    "kind": "microdata",
                    "path": "enhanced_frs_2024_25.h5",
                    "repo_id": "policyengine/policyengine-uk-data-private",
                    "revision": "1.58.0",
                    "sha256": "d" * 64,
                },
                "frs_2024_25": {
                    "kind": "microdata",
                    "path": "frs_2024_25.h5",
                    "repo_id": "policyengine/policyengine-uk-data-private",
                    "revision": "1.58.0",
                },
            },
        }
    )


def test_core_compatibility():
    pair = make_pair()
    result, evidence = core_compatibility(
        pair, _manifest(), model_requires_core=">=3.32.27"
    )
    assert result.status == "pass" and evidence["publisher_claim_covers_model"] is False
    result, _ = core_compatibility(
        pair, _manifest(["==2.126.8"], ["==3.33.0"]), model_requires_core=">=3.32.27"
    )
    assert result.details == {
        "publisher_claim_covers_model": True,
        "publisher_claim_covers_core": True,
    }
    result, _ = core_compatibility(pair, _manifest(), model_requires_core=">=3.34")
    assert result.status == "fail"


class _Response:
    def __init__(self, status, content=b""):
        self.status_code, self.content = status, content


def test_data_access():
    pair = make_pair()
    manifest_bytes = _manifest().model_dump_json().encode()
    pair = pair.model_copy(
        update={
            "data": pair.data.model_copy(
                update={
                    "release_manifest_sha256": hashlib.sha256(
                        manifest_bytes
                    ).hexdigest()
                }
            )
        }
    )

    def get(url, headers=None, timeout=None):
        return _Response(200 if headers else 401, manifest_bytes)

    def head(url, headers=None, timeout=None, allow_redirects=True):
        return _Response(200 if headers else 401)

    result, evidence, manifest = data_access(pair, get=get, head=head, token="t")
    assert result.status == "pass" and manifest is not None
    assert evidence["anonymous_dataset_status"] == 401
    result, _, _ = data_access(pair, get=get, head=head, token=None)
    assert result.status == "fail"
    result, _, _ = data_access(
        pair, get=get, head=lambda *a, **k: _Response(200), token="t"
    )
    assert result.status == "fail" and "without credentials" in result.summary
    result, _, _ = data_access(
        pair,
        get=get,
        head=lambda url, headers=None, **k: _Response(
            404
            if headers and "frs_2024_25.h5" in url and "enhanced" not in url
            else (200 if headers else 401)
        ),
        token="t",
    )
    assert result.status == "fail" and "frs_2024_25 returned HTTP 404" in result.summary


def _tiny_dataset(path: Path, year=2024, extra_person=None):
    person = pd.DataFrame(
        {
            "person_id": [1, 2],
            "age": [30.0, 5.0],
            "employment_income": [30000.0, 0.0],
            **(extra_person or {}),
        }
    )
    benunit = pd.DataFrame({"benunit_id": [1], "would_claim_uc": [True]})
    household = pd.DataFrame(
        {"household_id": [1], "household_weight": [100.0], "rent": [0.0]}
    )
    with pd.HDFStore(path, mode="w") as store:
        store.put("person", person)
        store.put("benunit", benunit)
        store.put("household", household)
        store.put("time_period", pd.Series([str(year)]))
    return path


def test_dataset_bytes(tmp_path):
    path = _tiny_dataset(tmp_path / "data.h5")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    pair = make_pair(dataset_sha=digest)
    pair = pair.model_copy(
        update={
            "data": pair.data.model_copy(update={"size_bytes": path.stat().st_size})
        }
    )
    assert dataset_bytes(pair, path)[0].status == "pass"
    assert dataset_bytes(make_pair(), path)[0].status == "fail"


@pytest.mark.parametrize(
    ("projected", "previous", "status"),
    [
        (list(range(2024, 2032)), list(range(2024, 2031)), "pass"),
        (list(range(2024, 2031)), list(range(2024, 2031)), "needs_review"),
        (list(range(2024, 2030)), list(range(2024, 2031)), "fail"),
        (list(range(2026, 2031)), None, "fail"),
        ([2020, 2021], None, "fail"),
    ],
)
def test_supported_years(tmp_path, projected, previous, status):
    path = _tiny_dataset(tmp_path / "data.h5", year=max(projected[0], 2024))
    result, evidence = supported_years(
        make_pair(),
        path,
        required_years=list(range(2025, 2031)),
        budget_horizon_years=list(range(2026, 2032)),
        previous_supported_years=previous,
        projected_years=lambda _: projected,
    )
    assert result.status == status, result.summary


# --- Budget inputs -------------------------------------------------------------------

INPUT_NAMES = [
    "age",
    "employment_income",
    "rent",
    "would_claim_uc",
    "household_weight",
    "new_input_a",
    "new_input_b",
]


def _tables(columns):
    tables = {
        "person": pd.DataFrame({"age": [30.0, 5.0], "employment_income": [3.0e4, 0.0]})
    }
    tables["household"] = pd.DataFrame(
        {"household_weight": [1.0, 2.0], "rent": [0.0, 9.0]}
    )
    tables["benunit"] = pd.DataFrame({"would_claim_uc": [True, False]})
    for entity in tables:
        tables[entity] = tables[entity][
            [c for c in tables[entity].columns if c in columns]
        ]
    return tables


@settings(max_examples=60, deadline=None)
@given(
    present=st.sets(st.sampled_from(INPUT_NAMES[:5]), min_size=1),
    previous=st.sets(st.sampled_from(INPUT_NAMES)),
)
def test_newly_missing_is_missing_now_minus_missing_before(present, previous):
    result, evidence = budget_inputs(
        make_pair(),
        Path("unused.h5"),
        model_input_variables=INPUT_NAMES,
        critical_inputs=[],
        accepted_gaps={},
        previous_missing_inputs=sorted(previous),
        previous_unusable_critical=[],
        tables=_tables(present),
    )
    missing = sorted(set(INPUT_NAMES) - present)
    assert evidence["missing_inputs"] == missing
    assert evidence["newly_missing_inputs"] == sorted(set(missing) - previous)


def test_critical_input_regression_fails_and_standing_gaps_need_review():
    common = dict(
        model_input_variables=INPUT_NAMES,
        accepted_gaps={},
        previous_missing_inputs=None,
    )
    result, _ = budget_inputs(
        make_pair(),
        Path("x"),
        critical_inputs=["rent", "age"],
        previous_unusable_critical=[],
        tables=_tables(
            {"age", "employment_income", "household_weight", "would_claim_uc"}
        ),
        **common,
    )
    assert result.status == "fail" and "rent (missing)" in result.summary
    degenerate = _tables(set(INPUT_NAMES))
    degenerate["household"]["rent"] = 0.0
    result, _ = budget_inputs(
        make_pair(),
        Path("x"),
        critical_inputs=["rent"],
        previous_unusable_critical=[],
        tables=degenerate,
        **common,
    )
    assert result.status == "fail" and "degenerate" in result.summary
    result, _ = budget_inputs(
        make_pair(),
        Path("x"),
        critical_inputs=["rent"],
        previous_unusable_critical=["rent"],
        tables=degenerate,
        **common,
    )
    assert result.status == "needs_review"
    result, _ = budget_inputs(
        make_pair(),
        Path("x"),
        critical_inputs=["rent"],
        previous_unusable_critical=["rent"],
        tables=degenerate,
        **{**common, "accepted_gaps": {"rent": "uk-data#999"}},
    )
    assert result.status == "pass"


def test_critical_inputs_file_lists_real_model_inputs():
    import json

    from policyengine_uk.system import system

    path = (
        Path(gates_module.__file__).resolve().parents[1]
        / "data"
        / "qualification"
        / "uk_budget_critical_inputs.json"
    )
    critical = json.loads(path.read_text())["critical"]
    not_inputs = [
        name
        for name in critical
        if name not in system.variables
        or not system.variables[name].is_input_variable()
    ]
    assert not_inputs == []


# --- Reform contract -----------------------------------------------------------------


def _declared_coverage(source):
    """ROUTES, CASES and PROPERTIES as a runner module declares them, read
    from a report of a full run (each case limited to the routes it ran on)."""

    source = source or {}
    by_case = {}
    for row in source.get("cases") or []:
        by_case.setdefault(row.get("case_id"), []).append(row)
    return {
        "ROUTES": tuple(source.get("routes") or ()),
        "CASES": tuple(
            SimpleNamespace(
                id=case,
                routes=tuple(dict.fromkeys(row.get("route") for row in rows)),
                checks=tuple(
                    SimpleNamespace(
                        target=label.split(":")[0],
                        name=label.split(":")[1],
                        year=int(label.split(":")[2]),
                        pending=next(
                            (
                                row.get("decision_id")
                                for row in rows
                                if row.get("check") == label
                            ),
                            None,
                        ),
                    )
                    for label in dict.fromkeys(row.get("check") for row in rows)
                    if label
                    and len(label.split(":")) == 3
                    and label.split(":")[0]
                    not in ("baseline_isolation", "unreformed_after_reform")
                ),
                expect_error="rejected"
                if any(row.get("check") == "rejected" for row in rows)
                else None,
            )
            for case, rows in by_case.items()
        ),
        "PROPERTIES": {
            row.get("property_id"): "" for row in source.get("properties") or []
        },
        "UNSUPPORTED_ROUTES": {
            row["route"]: row.get("reason", "")
            for row in source.get("cases") or []
            if row.get("status") == "unsupported"
            and row.get("check") is None
            and all(
                other.get("status") == "unsupported" and other.get("check") is None
                for other in source.get("cases") or []
                if other.get("route") == row["route"]
            )
        },
        "PENDING_DECISIONS": {
            row["decision_id"]
            for row in source.get("cases") or []
            if row.get("decision_id")
        },
        "POPULATION_CHECKS": tuple(
            dict.fromkeys(row["check_id"] for row in source.get("population") or [])
        ),
    }


def _importer(report=None, raises=None, missing=False, coverage=None, declare=True):
    """A runner module returning ``report``.

    It declares the coverage of ``coverage`` (a report of a full run), by
    default ``report`` itself, so a test of row statuses is not also a test
    of coverage.
    """

    def runner(**kwargs):
        if raises:
            raise raises
        return report

    def importer(name):
        if missing:
            raise ModuleNotFoundError(name)
        declared = (
            _declared_coverage(coverage if coverage is not None else report)
            if declare
            else {}
        )
        return SimpleNamespace(run_budget_reform_contract=runner, **declared)

    return importer


ENTRY = "policyengine.tax_benefit_models.uk.budget_reform_contract:run_budget_reform_contract"


@pytest.mark.parametrize(
    ("kwargs", "status"),
    [
        ({"missing": True}, "unavailable"),
        ({"raises": RuntimeError("boom")}, "error"),
        (
            {
                "report": {
                    "contract_version": "1.0.0",
                    "cases": [
                        {
                            "case_id": "april",
                            "route": "wrapper.policy",
                            "status": "pass",
                        }
                    ],
                }
            },
            "pass",
        ),
        (
            {
                "report": {
                    "cases": [
                        {
                            "case_id": "april",
                            "route": "country.reform_dict",
                            "status": "fail",
                        }
                    ]
                }
            },
            "fail",
        ),
        (
            {
                "report": {
                    "cases": [
                        {
                            "case_id": "api",
                            "route": "api.sim_api",
                            "status": "unsupported",
                        }
                    ]
                }
            },
            "error",
        ),
        (
            {
                "report": {
                    "cases": [
                        {
                            "case_id": "api",
                            "route": "api.sim_api",
                            "status": "unsupported",
                            "reason": "runs in sim-api",
                        },
                        {
                            "case_id": "freeze",
                            "route": "wrapper.policy",
                            "status": "pending",
                            "decision_id": "d1344",
                        },
                    ]
                }
            },
            "pass",
        ),
        ({"report": {"cases": []}}, "error"),
        (
            {
                "report": {
                    "cases": [{"case_id": "x", "route": "r", "status": "pass"}],
                    "properties": [
                        {"property_id": "baseline_isolation", "status": "fail"}
                    ],
                }
            },
            "fail",
        ),
    ],
)
def test_reform_contract_statuses(kwargs, status):
    result, _ = reform_contract(
        entrypoint=ENTRY,
        dataset_path=None,
        seed=0,
        max_examples=5,
        importer=_importer(**kwargs),
    )
    assert result.status == status, result.summary


def test_no_contract_configured_is_unavailable():
    assert (
        reform_contract(entrypoint=None, dataset_path=None, seed=0, max_examples=1)[
            0
        ].status
        == "unavailable"
    )


CONTRACT_FIXTURES = Path(__file__).parent / "fixtures" / "uk_contract"
CERTIFIED_SHA = "5ba399ea5ab9a6c7d4e9aaf6c623080beb34d9ad5f330f6244dbad72b8d960b6"
STATUS_RANK = {"pass": 0, "error": 1, "fail": 2}


def _fixture(name: str) -> dict:
    return json.loads((CONTRACT_FIXTURES / name).read_text())


def _recount(report: dict) -> dict:
    """Make a hand-edited report's summary and holds match its rows again."""

    summary = dict.fromkeys(("pass", "fail", "error", "unsupported", "pending"), 0)
    for section in ("cases", "properties", "population"):
        for row in report.get(section) or []:
            summary[row["status"]] += 1
    report["summary"] = summary
    report["holds"] = summary["fail"] == 0 and summary["error"] == 0
    return report


def _passing_report() -> dict:
    """W1's real full run: every route, 20 examples, the certified dataset."""

    return _fixture("full_allpass_uk_2.126.8.json")


def _run_contract(
    report, *, versions=None, dataset_sha=CERTIFIED_SHA, coverage=None, **kwargs
):
    """Gate ``report`` against the coverage of W1's real full run (or ``coverage``)."""

    kwargs.setdefault("seed", 0)
    kwargs.setdefault("max_examples", 20)
    kwargs.setdefault("dataset_path", Path("enhanced_frs_2024_25.h5"))
    return reform_contract(
        entrypoint=ENTRY,
        importer=_importer(
            report=report,
            coverage=coverage if coverage is not None else _passing_report(),
        ),
        expected_versions=versions
        or {"policyengine-uk": "2.126.8", "policyengine-core": "3.33.0"},
        expected_dataset_sha256=dataset_sha,
        **kwargs,
    )[0]


def test_the_released_models_full_run_passes_the_runners_own_declarations():
    """W1's full run on released policyengine-uk 2.126.12, gated against the
    coverage the merged runner module itself declares, so a stricter coverage
    rule cannot reject a real full run unnoticed."""

    import importlib
    import types

    from policyengine.tax_benefit_models.uk import budget_reform_contract as runner

    report = _fixture("full_released_uk_2.126.12.json")
    if runner.CONTRACT_VERSION != report["contract_version"]:
        pytest.skip(
            f"the runner declares contract {runner.CONTRACT_VERSION}; refresh "
            "tests/fixtures/uk_contract with a real full run"
        )
    proxy = types.ModuleType(runner.__name__)
    proxy.__dict__.update(vars(runner))
    proxy.run_budget_reform_contract = lambda **kwargs: report

    def importer(name):
        return proxy if name == runner.__name__ else importlib.import_module(name)

    result = reform_contract(
        entrypoint=ENTRY,
        importer=importer,
        expected_versions=report["versions"],
        expected_dataset_sha256=CERTIFIED_SHA,
        seed=0,
        max_examples=20,
        dataset_path=Path("enhanced_frs_2024_25.h5"),
    )[0]
    assert result.status == "pass", result.summary
    assert result.details["counts"] == {
        "pass": 673,
        "fail": 0,
        "error": 0,
        "unsupported": 79,
        "pending": 6,
    }


def test_w1_report_on_the_pinned_model_fails_on_its_defects():
    """W1's real report on policyengine-uk 2.125.1: 66 failures and 35 errors."""

    report = _fixture("pinned_uk_2.125.1_defects.json")
    result = _run_contract(
        report,
        versions={"policyengine-uk": "2.125.1", "policyengine-core": "3.33.0"},
        dataset_sha=None,
        dataset_path=None,
        max_examples=report["max_examples"],
        coverage=report,
    )
    assert result.status == "fail"
    assert result.summary.startswith("101 contract row(s) failed")
    assert result.details["problems"] == []


def test_w1_population_run_alone_is_incomplete():
    """W1's real population-only run has no cases and no sampled properties."""

    population_only = _fixture("population_pass_max_examples_0.json")
    result = _run_contract(population_only, max_examples=0, coverage=population_only)
    assert result.status == "error"
    problems = result.details["problems"]
    assert "the report has no cases" in problems
    assert any("annual_values_match_the_oracle did not run" in p for p in problems)


def test_w1_full_run_passes():
    """W1's real all-pass report: 267 pass, 6 pending d1344, 67 unsupported."""

    result = _run_contract(_passing_report())
    assert result.status == "pass", result.summary
    assert "every case, property and population check passed (267)" in result.summary
    assert "6 pending a methodology call" in result.summary
    assert result.details["problems"] == []


def _drop(report, **sections):
    """``report`` with rows removed, its summary and holds recounted."""

    return _recount({**report, **sections})


COVERAGE_GAPS = {
    "each case reduced to one check per route": lambda r: _drop(
        r,
        cases=list(
            {(row["case_id"], row["route"]): row for row in r["cases"]}.values()
        ),
    ),
    "all but one population check": lambda r: _drop(r, population=r["population"][:1]),
    "pending properties with invented decisions": lambda r: _drop(
        r,
        properties=[
            {**row, "status": "pending", "decision_id": "invented", "examples_run": 0}
            for row in r["properties"]
        ],
    ),
    "one case on one route": lambda r: (
        _drop(r, cases=r["cases"][:1], population=r["population"][:1], properties=[])
        | {"routes": r["routes"][:1]}
    ),
    "a route": lambda r: _drop(
        r, cases=[row for row in r["cases"] if row["route"] != "wrapper.policy"]
    ),
    "a route from the route list": lambda r: {**r, "routes": r["routes"][:-1]},
    "a case on one route": lambda r: _drop(
        r,
        cases=[
            row
            for row in r["cases"]
            if (row["case_id"], row["route"])
            != ("extended_freeze", "wrapper.household")
        ],
    ),
    "a sampled property": lambda r: _drop(r, properties=r["properties"][:1]),
    "every sampled property": lambda r: _drop(r, properties=[]),
    "the sampled examples": lambda r: {
        **r,
        "properties": [{**row, "examples_run": 0} for row in r["properties"]],
    },
    "most sampled examples": lambda r: {
        **r,
        "properties": [{**row, "examples_run": 19} for row in r["properties"]],
    },
}


@pytest.mark.parametrize("name", sorted(COVERAGE_GAPS))
def test_a_report_that_drops_coverage_does_not_qualify(name):
    """Interrupted review of #574: a recounted partial report passed, as did
    properties that passed on zero examples."""

    report = COVERAGE_GAPS[name](copy.deepcopy(_passing_report()))
    result = _run_contract(report)
    assert result.status == "error", (name, result.summary)


def test_a_runner_that_declares_no_coverage_cannot_qualify():
    report = _passing_report()
    result = reform_contract(
        entrypoint=ENTRY,
        dataset_path=Path("enhanced_frs_2024_25.h5"),
        seed=0,
        max_examples=20,
        expected_versions={"policyengine-uk": "2.126.8", "policyengine-core": "3.33.0"},
        expected_dataset_sha256=CERTIFIED_SHA,
        importer=_importer(report=report, declare=False),
    )[0]
    assert result.status == "error"
    assert "declares no ROUTES, CASES and PROPERTIES" in result.summary


def test_population_coverage_uses_the_population_runners_declarations():
    """A check added by the runner must be required without a gate-side list."""

    report = _passing_report()
    importer = _importer(report=report, coverage=report)
    module = importer("contract")
    del module.POPULATION_CHECKS
    population = SimpleNamespace()
    population.__doc__ = (
        "Checks:\n\n``new_population_check``\n    Declared by the population runner."
    )
    result = reform_contract(
        entrypoint=ENTRY,
        dataset_path=Path("dataset.h5"),
        seed=0,
        max_examples=20,
        importer=lambda name: (
            population if name.endswith("budget_reform_population") else module
        ),
    )[0]
    assert result.status == "error"
    assert "new_population_check" in result.summary


REPORT_TAMPERING = {
    "invented pending decision": lambda r: _recount(
        {
            **r,
            "cases": [
                {**row, "decision_id": "invented"}
                if row["status"] == "pending"
                else row
                for row in r["cases"]
            ],
        }
    ),
    "other model": lambda r: r["versions"].update({"policyengine-uk": "2.125.1"}),
    "other core": lambda r: r["versions"].update({"policyengine-core": "3.30.0"}),
    "other dataset": lambda r: r["dataset"].update(sha256="0" * 64),
    "no population": lambda r: _recount({**r, "population": []}),
    "other seed": lambda r: r.update(seed=7),
    "fewer examples": lambda r: r.update(max_examples=5),
    "summary": lambda r: r["summary"].update(
        unsupported=r["summary"]["unsupported"] + 1
    ),
    "holds": lambda r: r.update(holds=False),
    "pending without decision": lambda r: _recount(
        {**r, "cases": [{**r["cases"][0], "status": "pending"}, *r["cases"][1:]]}
    ),
    "unsupported without reason": lambda r: _recount(
        {
            **r,
            "population": [
                {**r["population"][0], "status": "unsupported"},
                *r["population"][1:],
            ],
        }
    ),
}


@pytest.mark.parametrize("name", sorted(REPORT_TAMPERING))
def test_a_report_that_is_not_a_full_run_of_this_candidate_is_an_error(name):
    report = copy.deepcopy(_passing_report())
    tampered = REPORT_TAMPERING[name](report) or report
    assert _run_contract(tampered).status == "error"


@settings(max_examples=40, deadline=None)
@given(
    data=st.data(),
    worse=st.sampled_from(["fail", "error"]),
    section=st.sampled_from(["cases", "properties", "population"]),
)
def test_a_worse_row_never_improves_the_gate(data, worse, section):
    """Monotone: turning any row into a failure fails the gate."""

    report = _passing_report()
    index = data.draw(st.integers(0, len(report[section]) - 1))
    report[section][index] = {**report[section][index], "status": worse}
    result = _run_contract(_recount(report))
    assert STATUS_RANK[result.status] >= STATUS_RANK["fail"]


# --- Metrics review ------------------------------------------------------------------

BOUNDS = {
    "default": {"relative": 0.02, "absolute": 5e8},
    "kinds": {"poverty": {"relative": 0.0, "absolute": 0.005}},
}


def _report(values, **extra):
    return {
        "status": "ok",
        "metrics_version": "m1",
        "partition_version": "p1",
        "metrics": [
            {"metric_id": mid, "year": year, "value": value, "kind": kind}
            for (mid, year, kind), value in values.items()
        ],
        # Every real report carries checks; one always passes here.
        "identities": [
            {"identity_id": "weights:household", "status": "pass"},
            *extra.pop("identities", []),
        ],
        **extra,
    }


BASE = {
    ("income_tax", 2027, "receipt"): 3.0e11,
    ("relative_poverty", 2027, "poverty"): 0.17,
}


def test_metric_comparison_rules():
    assert compare_metric_reports(_report(BASE), _report(BASE), BOUNDS)[0] == "pass"
    moved = {**BASE, ("income_tax", 2027, "receipt"): 3.1e11}
    assert (
        compare_metric_reports(_report(moved), _report(BASE), BOUNDS)[0]
        == "needs_review"
    )
    assert (
        compare_metric_reports(
            _report(BASE, metrics_version="m2"), _report(BASE), BOUNDS
        )[0]
        == "fail"
    )
    assert (
        compare_metric_reports(
            _report(BASE, partition_version="p2"), _report(BASE), BOUNDS
        )[0]
        == "needs_review"
    )
    lost = {("income_tax", 2027, "receipt"): 3.0e11}
    assert compare_metric_reports(_report(lost), _report(BASE), BOUNDS)[0] == "fail"
    nan = {**BASE, ("income_tax", 2027, "receipt"): float("nan")}
    assert compare_metric_reports(_report(nan), _report(BASE), BOUNDS)[0] == "fail"
    warned = _report(
        BASE, identities=[{"identity_id": "inert:alcohol_duty", "status": "warn"}]
    )
    status, _, evidence = compare_metric_reports(warned, _report(BASE), BOUNDS)
    assert status == "pass" and evidence["warn_identities"] == ["inert:alcohol_duty"]


def test_reports_that_measure_nothing_fail():
    """Interrupted review of #574: two empty reports compared as a pass."""

    assert compare_metric_reports({}, {}, BOUNDS)[0] == "fail"
    full = _report(BASE)
    for broken in (
        {**full, "metrics": []},
        {**full, "identities": []},
        {**full, "status": "error"},
        {key: value for key, value in full.items() if key != "status"},
    ):
        assert compare_metric_reports(broken, full, BOUNDS)[0] == "fail"
        assert compare_metric_reports(full, broken, BOUNDS)[0] == "fail"


@pytest.mark.parametrize("status", ["error", "unsupported", "pending", None, "PASS"])
def test_a_check_with_an_unknown_status_is_not_a_pass(status):
    candidate = _report(BASE, identities=[{"identity_id": "closure", "status": status}])
    previous = _report(BASE, identities=[{"identity_id": "closure", "status": "pass"}])
    result = compare_metric_reports(candidate, previous, BOUNDS)
    assert result[0] == "fail" and "unknown status" in result[1]


def test_a_check_that_disappears_is_lost_coverage():
    previous = _report(
        BASE,
        identities=[
            {"identity_id": "closure", "status": "pass"},
            {"identity_id": "sign:vat", "status": "pass"},
        ],
    )
    # A hard check that vanished under the same partition fails.
    no_closure = _report(
        BASE, identities=[{"identity_id": "sign:vat", "status": "pass"}]
    )
    result = compare_metric_reports(no_closure, previous, BOUNDS)
    assert result[0] == "fail" and "checks disappeared: closure" in result[1]
    # A no-worsening check that vanished needs a look.
    no_sign = _report(BASE, identities=[{"identity_id": "closure", "status": "pass"}])
    assert compare_metric_reports(no_sign, previous, BOUNDS)[0] == "needs_review"
    # When the model's partition changed, vanished per-head checks need review.
    repartitioned = _report(
        BASE,
        partition_version="p2",
        identities=[{"identity_id": "sign:vat", "status": "pass"}],
    )
    assert compare_metric_reports(repartitioned, previous, BOUNDS)[0] == "needs_review"


def _checks(**statuses):
    return [
        {"identity_id": key.replace("__", ":"), "status": value}
        for key, value in statuses.items()
    ]


@pytest.mark.parametrize(
    ("candidate", "previous", "status"),
    [
        # Hard checks fail whatever the previous pair did.
        ({"finite__vat": "fail"}, {"finite__vat": "fail"}, "fail"),
        ({"closure": "fail"}, {}, "fail"),
        (
            {"identity__partition_sum": "fail"},
            {"identity__partition_sum": "pass"},
            "fail",
        ),
        ({"determinism__repeat": "fail"}, {}, "fail"),
        # Unknown check kinds are treated as hard: no silent skips.
        ({"newkind__x": "fail"}, {"newkind__x": "fail"}, "fail"),
        # Known-defect checks fail only as regressions.
        (
            {"counted_once__statutory_sick_pay": "fail"},
            {"counted_once__statutory_sick_pay": "fail"},
            "pass",
        ),
        (
            {"counted_once__statutory_sick_pay": "fail"},
            {"counted_once__statutory_sick_pay": "pass"},
            "fail",
        ),
        ({"sign__vat": "fail"}, {}, "fail"),
        ({"bounds__uc": "fail"}, {"bounds__uc": "fail"}, "pass"),
        # The overlap guard fails on main for a known defect: no-worsening.
        (
            {"overlap_guard__property_transaction_tax_geography": "fail"},
            {"overlap_guard__property_transaction_tax_geography": "fail"},
            "pass",
        ),
        (
            {"overlap_guard__property_transaction_tax_geography": "fail"},
            {"overlap_guard__property_transaction_tax_geography": "pass"},
            "fail",
        ),
        # A check skipped before that fails now has worsened.
        (
            {"counted_once__statutory_sick_pay": "fail"},
            {"counted_once__statutory_sick_pay": "skipped"},
            "fail",
        ),
        # Skipped is neither a pass nor a failure, but losing a passing
        # check needs a look.
        (
            {"counted_once__winter_fuel": "skipped"},
            {"counted_once__winter_fuel": "skipped"},
            "pass",
        ),
        (
            {"counted_once__winter_fuel": "skipped"},
            {"counted_once__winter_fuel": "pass"},
            "needs_review",
        ),
        # The reform checks are hard, whatever the previous pair did.
        (
            {"responsive__state_pension_plus_10pc": "fail"},
            {"responsive__state_pension_plus_10pc": "fail"},
            "fail",
        ),
        (
            {"reform_runs__uc_taper_20pc": "fail"},
            {"reform_runs__uc_taper_20pc": "fail"},
            "fail",
        ),
        # Warnings are recorded; a check that newly warns needs review.
        ({"inert__tobacco_duty": "warn"}, {"inert__tobacco_duty": "warn"}, "pass"),
        (
            {"inert__tobacco_duty": "warn"},
            {"inert__tobacco_duty": "pass"},
            "needs_review",
        ),
    ],
)
def test_check_classification(candidate, previous, status):
    result = compare_metric_reports(
        _report(BASE, identities=_checks(**candidate)),
        _report(BASE, identities=_checks(**previous)),
        BOUNDS,
    )
    assert result[0] == status, result[1]


def test_a_known_failure_that_spreads_to_more_years_has_worsened():
    """No-worsening by scope: the failing scopes must be a subset of the previous pair's."""

    def check(scopes):
        return _report(
            BASE,
            identities=[
                {
                    "identity_id": "sign:vat",
                    "status": "fail",
                    "failing_scopes": scopes,
                }
            ],
        )

    same = compare_metric_reports(
        check(["2026", "2027"]), check(["2026", "2027"]), BOUNDS
    )
    fewer = compare_metric_reports(check(["2026"]), check(["2026", "2027"]), BOUNDS)
    more = compare_metric_reports(
        check(["2026", "2028"]), check(["2026", "2027"]), BOUNDS
    )
    assert (same[0], fewer[0], more[0]) == ("pass", "pass", "fail")
    assert "sign:vat (fails in more scopes)" in more[1]
    # Without scopes on both sides the failures cannot be told apart.
    unscoped = _report(BASE, identities=[{"identity_id": "sign:vat", "status": "fail"}])
    assert (
        compare_metric_reports(check(["2026", "2028"]), unscoped, BOUNDS)[0] == "pass"
    )


@settings(max_examples=150, deadline=None)
@given(
    changes=st.lists(
        st.floats(min_value=-0.5, max_value=0.5, allow_nan=False),
        min_size=2,
        max_size=2,
    ),
    shrink=st.floats(min_value=0.0, max_value=1.0),
)
def test_shrinking_moves_never_worsens_the_status(changes, shrink):
    order = {"pass": 0, "needs_review": 1, "fail": 2}
    keys = list(BASE)

    def candidate(scale):
        return _report(
            {
                key: BASE[key] * (1 + scale * change)
                for key, change in zip(keys, changes)
            }
        )

    full = compare_metric_reports(candidate(1.0), _report(BASE), BOUNDS)[0]
    smaller = compare_metric_reports(candidate(shrink), _report(BASE), BOUNDS)[0]
    assert order[smaller] <= order[full]


def test_metrics_gate_splits_model_and_data_steps():
    cross = {**BASE, ("income_tax", 2027, "receipt"): 3.2e11}
    result, evidence = metrics_review(
        candidate_report=_report(cross),
        previous_report=_report(BASE),
        bounds=BOUNDS,
        cross_report=_report(cross),
    )
    assert result.details == {"model_only": "needs_review", "data_only": "pass"}
    assert result.status == "needs_review"
    assert (
        metrics_review(candidate_report=None, previous_report=None, bounds=BOUNDS)[
            0
        ].status
        == "unavailable"
    )


# --- Orchestration -------------------------------------------------------------------


@settings(max_examples=50, deadline=None)
@given(
    outcomes=st.lists(
        st.sampled_from(["pass", "fail", "raise"]), min_size=1, max_size=9
    )
)
def test_run_gates_returns_one_result_per_gate(outcomes):
    def make(index, outcome):
        def function():
            if outcome == "raise":
                raise RuntimeError(f"gate {index} crashed")
            return gates_module._result(f"wrong-id-{index}", outcome, "x", {})

        return (f"gate_{index}", function)

    results, evidence = run_gates([make(i, o) for i, o in enumerate(outcomes)])
    assert [r.gate_id for r in results] == [f"gate_{i}" for i in range(len(outcomes))]
    for result, outcome in zip(results, outcomes):
        assert result.status == ("error" if outcome == "raise" else outcome)
    assert set(evidence) == {f"gate_{i}" for i in range(len(outcomes))}


# --- Previous-pair runners -----------------------------------------------------------


def _write_previous_receipt(root, pair, evidence, *, attempt="a"):
    from policyengine.provenance.qualification_ledger import write_json

    receipt = make_receipt(pair)
    receipt = receipt.model_copy(
        update={
            "gates": [
                gate.model_copy(
                    update={
                        "evidence_sha256": gates_module.evidence_sha256(
                            evidence[gate.gate_id]
                        )
                    }
                )
                if gate.gate_id in evidence
                else gate
                for gate in receipt.gates
            ]
        }
    )
    pair_dir = root / "uk" / pair.pair_id
    write_json(pair_dir / "qualification_receipt.json", receipt.canonical_payload())
    attempt_dir = pair_dir / "attempts" / attempt
    write_json(attempt_dir / "qualification_receipt.json", receipt.canonical_payload())
    write_json(attempt_dir / "harness.json", receipt.harness.canonical_payload())
    for gate_id, value in evidence.items():
        write_json(attempt_dir / "gates" / f"{gate_id}.json", value)
    return receipt, attempt_dir


def _previous_identity(pair):
    return {
        "bundle_version": HARNESS.policyengine_version,
        "model_version": pair.model.version,
        "core_version": pair.core.version,
        "data_release_version": pair.data.release_version,
        "dataset_sha256": pair.data.dataset_sha256,
        "qualification_pair_id": pair.pair_id,
        "model_wheel_sha256": pair.model.wheel_sha256,
        "core_wheel_sha256": pair.core.wheel_sha256,
    }


def test_previous_evidence_matches_the_exact_certified_core_and_wheels(tmp_path):
    wrong = make_pair(core="3.32.0")
    certified = make_pair(core="3.33.0")
    wrong_evidence = {
        "supported_years": {"supported_years": [2025]},
        "budget_inputs": {"missing_inputs": ["age"], "unusable_critical": []},
    }
    expected = {
        "supported_years": {"supported_years": [2025, 2026]},
        "budget_inputs": {"missing_inputs": [], "unusable_critical": []},
    }
    _write_previous_receipt(tmp_path, wrong, wrong_evidence)
    _write_previous_receipt(tmp_path, certified, expected)
    assert (
        gates_module._previous_gate_evidence(tmp_path, _previous_identity(certified))
        == expected
    )
    for wheel in ("core_wheel_sha256", "model_wheel_sha256"):
        altered = {**_previous_identity(certified), wheel: "0" * 64}
        assert gates_module._previous_gate_evidence(tmp_path, altered) == {}


def test_previous_evidence_belongs_to_the_receipts_attempt(tmp_path):
    from policyengine.provenance.qualification_ledger import write_json

    pair = make_pair()
    expected = {
        "supported_years": {"supported_years": [2025, 2026]},
        "budget_inputs": {"missing_inputs": [], "unusable_critical": []},
    }
    receipt, attempt = _write_previous_receipt(tmp_path, pair, expected)
    unrelated = attempt.parent / "z"
    other_receipt = receipt.model_copy(
        update={"harness": HARNESS.model_copy(update={"git_commit": "1" * 40})}
    )
    write_json(
        unrelated / "qualification_receipt.json", other_receipt.canonical_payload()
    )
    for name in expected:
        write_json(unrelated / "gates" / f"{name}.json", {"untrusted": True})
    assert (
        gates_module._previous_gate_evidence(tmp_path, _previous_identity(pair))
        == expected
    )


@pytest.mark.parametrize(
    "corruption", ["digest", "shape", "receipt", "missing identity"]
)
def test_unverified_previous_evidence_is_recomputed(tmp_path, corruption):
    from policyengine.provenance.qualification_ledger import write_json

    pair = make_pair()
    expected = {
        "supported_years": {"supported_years": [2025, 2026]},
        "budget_inputs": {"missing_inputs": [], "unusable_critical": []},
    }
    receipt, attempt = _write_previous_receipt(tmp_path, pair, expected)
    previous = _previous_identity(pair)
    if corruption == "digest":
        write_json(
            attempt / "gates" / "supported_years.json", {"supported_years": [2025]}
        )
    elif corruption == "shape":
        invalid = {**expected, "supported_years": {"supported_years": [True]}}
        _write_previous_receipt(tmp_path, pair, invalid)
    elif corruption == "receipt":
        payload = receipt.canonical_payload() | {"verdict": "needs_review"}
        write_json(attempt.parent.parent / "qualification_receipt.json", payload)
    else:
        previous.pop("qualification_pair_id")
        previous.pop("core_wheel_sha256")
    assert gates_module._previous_gate_evidence(tmp_path, previous) == {}


@pytest.mark.parametrize("corrupt_baseline", [False, True])
def test_orchestration_hashes_every_finalized_gate_evidence(
    tmp_path, monkeypatch, corrupt_baseline
):
    from policyengine.provenance import dataset_materialization
    from policyengine.provenance.qualification_ledger import write_json

    pair = make_pair()
    config = json.loads(
        (
            Path(__file__).parents[1] / "src/policyengine/data/qualification/uk.json"
        ).read_text()
    )
    monkeypatch.setattr(
        dataset_materialization,
        "materialize_dataset",
        lambda *a, **k: SimpleNamespace(path=tmp_path / "dataset.h5"),
    )
    monkeypatch.setitem(
        sys.modules,
        "policyengine_uk.system",
        SimpleNamespace(system=SimpleNamespace(variables={})),
    )
    baseline = {
        "budget_inputs": {"missing_inputs": [], "unusable_critical": []},
        "supported_years": {"supported_years": [2025]},
    }
    _, attempt = _write_previous_receipt(tmp_path, pair, baseline)
    if corrupt_baseline:
        write_json(
            attempt / "gates" / "supported_years.json", {"supported_years": [2024]}
        )
    snapshots = []

    def snapshot(*args, **kwargs):
        snapshots.append(args[0])
        return {
            "missing_inputs": [],
            "unusable_critical": [],
            "supported_years": [2025],
        }

    monkeypatch.setattr(gates_module, "run_inputs_snapshot", snapshot)
    monkeypatch.setattr(gates_module, "vendor_metrics_tool", lambda *a, **k: tmp_path)
    monkeypatch.setattr(gates_module, "load_standard_reforms", lambda *a: [])
    monkeypatch.setattr(gates_module, "previous_pair_python", lambda *a: "python")
    monkeypatch.setattr(
        gates_module,
        "run_metrics_report",
        lambda *a, **k: {"partition_source": "test", "dataset_path": "dataset.h5"},
    )
    monkeypatch.setattr(
        gates_module, "_download", lambda *a, **k: tmp_path / "wheel.whl"
    )
    for name in (
        "installed_versions",
        "wheel_hashes",
        "core_compatibility",
        "dataset_bytes",
        "supported_years",
        "budget_inputs",
        "reform_contract",
        "metrics_review",
        "reform_responsiveness",
    ):
        monkeypatch.setattr(
            gates_module,
            name,
            lambda *a, _name=name, **k: gates_module._result(
                _name, "pass", "test", {"before_metadata": _name}
            ),
        )
    monkeypatch.setattr(
        gates_module,
        "data_access",
        lambda *a, **k: (*gates_module._result("data_access", "pass", "test", {}), {}),
    )
    resolved = SimpleNamespace(
        pair=pair,
        model_wheel=SimpleNamespace(
            url="model", filename="model.whl", sha256=pair.model.wheel_sha256
        ),
        core_wheel=SimpleNamespace(
            url="core", filename="core.whl", sha256=pair.core.wheel_sha256
        ),
        model_requires_core=">=3.0",
    )
    results, evidence = gates_module.run_candidate_gates(
        resolved,
        HARNESS,
        config=config,
        work_dir=tmp_path,
        previous_certificate=_previous_identity(pair),
        ledger_root=tmp_path,
    )
    mismatches = [
        result.gate_id
        for result in results
        if result.evidence_sha256
        != gates_module.evidence_sha256(evidence[result.gate_id])
    ]
    assert mismatches == []
    assert snapshots == (["python"] if corrupt_baseline else [])
    assert evidence["budget_inputs"]["previous_source"] == (
        f"computed with policyengine {HARNESS.policyengine_version}"
        if corrupt_baseline
        else "ledger"
    )


@settings(max_examples=15, deadline=None)
@given(
    present=st.sets(st.sampled_from(["age", "employment_income", "rent"]), min_size=1),
    critical=st.lists(
        st.sampled_from(["age", "rent", "would_claim_uc", "missing_x"]),
        unique=True,
        max_size=3,
    ),
    projected=st.lists(st.integers(2022, 2032), min_size=1, max_size=6, unique=True),
)
def test_inputs_runner_agrees_with_the_gates(
    tmp_path_factory, present, critical, projected
):
    """Differential: the previous-pair runner and the in-process gates agree."""

    import sys

    from policyengine.provenance.uk_candidate import (
        dataset_columns,
        run_inputs_snapshot,
    )

    directory = tmp_path_factory.mktemp("runner")
    extra = {"rent_person": [1.0, 0.0]} if "rent" in present else {}
    path = _tiny_dataset(directory / "data.h5", year=2024, extra_person=extra)
    inputs = [
        "age",
        "employment_income",
        "rent",
        "would_claim_uc",
        "household_weight",
        "missing_x",
    ]
    snapshot = run_inputs_snapshot(
        sys.executable,
        critical=critical,
        out=directory / "snapshot.json",
        dataset_path=path,
        model_input_variables=inputs,
        projected_years=projected,
    )
    tables = dataset_columns(path)
    _, evidence = budget_inputs(
        make_pair(),
        path,
        model_input_variables=inputs,
        critical_inputs=critical,
        accepted_gaps={},
        previous_missing_inputs=None,
        previous_unusable_critical=None,
        tables=tables,
    )
    assert snapshot["missing_inputs"] == evidence["missing_inputs"]
    assert snapshot["unusable_critical"] == evidence["unusable_critical"]
    _, years = supported_years(
        make_pair(),
        path,
        required_years=[],
        budget_horizon_years=[],
        previous_supported_years=None,
        projected_years=lambda _: sorted(projected),
    )
    assert snapshot["supported_years"] == years["supported_years"]


STANDARD_REFORMS_FIXTURE = (
    Path(__file__).parent / "fixtures" / "uk_metrics" / "standard_reforms.yaml"
)


def _tool_tarball(commit="c" * 40, include_partition=True, include_reforms=True):
    import tarfile

    buffer = io.BytesIO()
    prefix = f"policyengine-uk-{commit}"
    files = {
        f"{prefix}/policyengine_uk/utils/aggregate_impact/__init__.py": b"TOOL_SCHEMA = 'x/1'\n",
        f"{prefix}/policyengine_uk/utils/aggregate_impact/api.py": b"def compute_budget_metrics(sim, **kwargs):\n    return {}\n",
        f"{prefix}/policyengine_uk/utils/other.py": b"not copied\n",
    }
    if include_partition:
        files[f"{prefix}/policyengine_uk/data/fiscal_partition.yaml"] = b"heads: []\n"
    if include_reforms:
        files[
            f"{prefix}/policyengine_uk/utils/aggregate_impact/standard_reforms.yaml"
        ] = STANDARD_REFORMS_FIXTURE.read_bytes()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_metrics_tool_is_vendored_from_one_commit(tmp_path):
    from policyengine.provenance.uk_candidate import vendor_metrics_tool

    calls = []

    def get(url, timeout=None):
        calls.append(url)
        response = SimpleNamespace(
            content=_tool_tarball(), raise_for_status=lambda: None
        )
        return response

    tool = {
        "repository": "PolicyEngine/policyengine-uk",
        "commit": "c" * 40,
        "path": "policyengine_uk/utils/aggregate_impact",
    }
    root = vendor_metrics_tool(tool, tmp_path, get=get)
    assert calls == [
        f"https://codeload.github.com/PolicyEngine/policyengine-uk/tar.gz/{'c' * 40}"
    ]
    assert sorted(p.name for p in (root / "pe_uk_aggregate_impact").iterdir()) == [
        "__init__.py",
        "api.py",
        "standard_reforms.yaml",
    ]
    assert (root / "fiscal_partition.yaml").read_text() == "heads: []\n"
    assert (
        vendor_metrics_tool(
            tool, tmp_path, get=lambda *a, **k: pytest.fail("refetched")
        )
        == root
    )


def test_metrics_report_runner_command(tmp_path):
    import json as _json

    from policyengine.provenance.uk_candidate import METRICS_RUNNER, run_metrics_report

    seen = {}

    def run(command, check, cwd):
        seen["command"] = command
        Path(command[-1]).write_text(_json.dumps({"status": "ok", "metrics": []}))

    report = run_metrics_report(
        "/venv/bin/python",
        tmp_path / "tool",
        years=[2026, 2027],
        out=tmp_path / "report.json",
        dataset_path=tmp_path / "data.h5",
        run=run,
    )
    assert report == {"status": "ok", "metrics": []}
    python, flag, code, vendor, settings, out = seen["command"]
    assert (python, flag, code) == ("/venv/bin/python", "-c", METRICS_RUNNER)
    assert _json.loads(settings)["years"] == [2026, 2027]
    assert _json.loads(settings)["run_guard"] is True
    # The runner must not pass ``reforms``: the tool then costs its own
    # standard set, whereas an empty list would cost none.
    assert "reforms=" not in METRICS_RUNNER


def test_the_standard_reforms_are_read_from_the_vendored_tool(tmp_path):
    from policyengine.provenance.uk_candidate import (
        load_standard_reforms,
        vendor_metrics_tool,
    )

    tool = {
        "repository": "PolicyEngine/policyengine-uk",
        "commit": "c" * 40,
        "path": "policyengine_uk/utils/aggregate_impact",
    }
    root = vendor_metrics_tool(
        tool,
        tmp_path,
        get=lambda url, timeout=None: SimpleNamespace(
            content=_tool_tarball(), raise_for_status=lambda: None
        ),
    )
    reforms = load_standard_reforms(root, "standard_reforms.yaml")
    assert len(reforms) == 10
    assert reforms[0] == {
        "id": "basic_rate_plus_1pp",
        "name": "Raise basic rate by 1pp",
        "variable": "income_tax",
        "direction": "up",
        "minimum": 1.5e9,
    }
    assert {reform["id"] for reform in reforms} >= {
        "uc_standard_allowance_plus_10pc",
        "state_pension_plus_10pc",
    }
    with pytest.raises(ValueError, match="ships no"):
        load_standard_reforms(root, "missing.yaml")


@pytest.mark.parametrize(
    "entry",
    [
        {
            "name": "No id",
            "responds": {"variable": "x", "direction": "up", "minimum": 1},
        },
        {"id": "no_response", "name": "No response"},
        {
            "id": "bad",
            "responds": {"variable": "x", "direction": "sideways", "minimum": 1},
        },
        {"id": "zero", "responds": {"variable": "x", "direction": "up", "minimum": 0}},
    ],
    ids=["no id", "no response", "bad direction", "zero minimum"],
)
def test_a_standard_reform_without_a_stated_response_is_refused(tmp_path, entry):
    import yaml

    from policyengine.provenance.uk_candidate import load_standard_reforms

    package = tmp_path / "pe_uk_aggregate_impact"
    package.mkdir()
    (package / "standard_reforms.yaml").write_text(yaml.safe_dump({"reforms": [entry]}))
    with pytest.raises(ValueError):
        load_standard_reforms(tmp_path, "standard_reforms.yaml")


# --- Reform responsiveness -----------------------------------------------------------

RESPONSE_YEARS = [2025, 2026, 2027, 2028, 2029, 2030, 2031]


def _standard_reforms(tmp_path_factory=None):
    import yaml

    return [
        {
            "id": entry["id"],
            "name": entry["name"],
            "variable": entry["responds"]["variable"],
            "direction": entry["responds"]["direction"],
            "minimum": float(entry["responds"]["minimum"]),
        }
        for entry in yaml.safe_load(STANDARD_REFORMS_FIXTURE.read_text())["reforms"]
    ]


def _tool_check(reform, changes):
    """The tool's responsive verdict, restated from reforms.responsiveness()."""

    sign = 1.0 if reform["direction"] == "up" else -1.0
    return bool(changes) and all(
        sign * change >= reform["minimum"] for change in changes.values()
    )


def _responsive_report(scale=5.0, overrides=None, years=RESPONSE_YEARS, lie=None):
    """A report in which each reform moves its target by scale x its minimum.

    ``overrides`` replaces single values (None removes the row). The
    ``responsive`` checks follow the tool's rule, unless ``lie`` names a
    reform id whose check is inverted.
    """

    overrides = overrides or {}
    metrics, identities = [], []
    for reform in _standard_reforms():
        sign = 1.0 if reform["direction"] == "up" else -1.0
        changes = {}
        for year in years:
            value = overrides.get(
                (reform["id"], year), sign * reform["minimum"] * scale
            )
            if value is not None:
                changes[year] = value
                metrics.append(
                    {
                        "metric_id": f"reform_targets.{reform['id']}",
                        "year": year,
                        "value": value,
                        "kind": "reform_target",
                    }
                )
        finite = {y: v for y, v in changes.items() if v == v}
        ok = len(finite) == len(years) and _tool_check(reform, finite)
        if lie == reform["id"]:
            ok = not ok
        identities.append(
            {"identity_id": f"reform_runs:{reform['id']}", "status": "pass"}
        )
        identities.append(
            {
                "identity_id": f"responsive:{reform['id']}",
                "status": "pass" if ok else "fail",
                "detail": "" if ok else f"expected {reform['variable']} to move",
            }
        )
    return {
        "status": "ok",
        "years": list(years),
        "metrics": metrics,
        "identities": identities,
    }


def _responsiveness(report, reforms=None, years=RESPONSE_YEARS):
    from policyengine.provenance.uk_candidate import reform_responsiveness

    return reform_responsiveness(
        report=report,
        standard_reforms=_standard_reforms() if reforms is None else reforms,
        years=years,
    )[0]


def test_reforms_that_all_respond_pass():
    result = _responsiveness(_responsive_report())
    assert result.status == "pass", result.summary
    assert "All 10 standard reforms" in result.summary
    assert "2025-26 to 2031-32" in result.summary


UC_ALLOWANCE = "uc_standard_allowance_plus_10pc"
STATE_PENSION = "state_pension_plus_10pc"


@pytest.mark.parametrize(
    ("overrides", "reform_id"),
    [
        ({(UC_ALLOWANCE, year): 0.0 for year in RESPONSE_YEARS}, UC_ALLOWANCE),
        ({(STATE_PENSION, year): 4.0e7 for year in RESPONSE_YEARS}, STATE_PENSION),
        ({(UC_ALLOWANCE, 2027): 0.0}, UC_ALLOWANCE),
        ({(STATE_PENSION, 2031): -1.3e10}, STATE_PENSION),
        ({("basic_rate_plus_1pp", 2030): None}, "basic_rate_plus_1pp"),
        ({("basic_rate_plus_1pp", 2030): float("nan")}, "basic_rate_plus_1pp"),
    ],
    ids=[
        "exactly zero",
        "nearly inert",
        "one inert year",
        "wrong sign",
        "missing",
        "nan",
    ],
)
def test_a_reform_that_does_not_respond_fails_qualification(overrides, reform_id):
    """The backtest's two modes (exactly £0, nearly inert) and their neighbours."""

    result = _responsiveness(_responsive_report(overrides=overrides))
    assert result.status == "fail"
    assert f"({reform_id}) did not respond" in result.summary, result.summary


def test_a_run_that_costed_no_reforms_cannot_pass():
    """Presence is required: an empty or partial check set is a failure."""

    report = _responsive_report()
    report["identities"] = []
    result = _responsiveness(report)
    assert result.status == "fail" and "did not run" in result.summary
    report = _responsive_report()
    report["identities"] = [
        row
        for row in report["identities"]
        if row["identity_id"] != f"responsive:{STATE_PENSION}"
    ]
    result = _responsiveness(report)
    assert result.status == "fail"
    assert "no responsive check in the report" in result.summary
    report = _responsive_report()
    for row in report["identities"]:
        if row["identity_id"] == f"reform_runs:{UC_ALLOWANCE}":
            row["status"] = "fail"
    assert f"({UC_ALLOWANCE}) did not run" in _responsiveness(report).summary


def test_the_tools_verdict_is_checked_against_its_own_numbers():
    """Differential: a pass the reform_targets values do not support is an error."""

    inert = {(UC_ALLOWANCE, year): 0.0 for year in RESPONSE_YEARS}
    lying_pass = _responsive_report(overrides=inert, lie=UC_ALLOWANCE)
    result = _responsiveness(lying_pass)
    assert result.status == "error"
    assert "do not meet the minimum" in result.summary
    lying_fail = _responsive_report(lie=STATE_PENSION)
    assert _responsiveness(lying_fail).status == "fail"
    short = _responsive_report(years=RESPONSE_YEARS[:-1])
    assert _responsiveness(short).status in ("fail", "error")


def test_responsiveness_is_never_skipped_or_guessed():
    from policyengine.provenance.qualification import (
        REQUIRED_GATES,
        GateResult,
        qualification_verdict,
    )

    assert _responsiveness(None).status == "unavailable"
    assert _responsiveness(_responsive_report(), reforms=[]).status == "unavailable"
    assert "reform_responsiveness" in REQUIRED_GATES
    for status, verdict in (("unavailable", "incomplete"), ("fail", "rejected")):
        gates = [
            GateResult(
                gate_id=name,
                status=status if name == "reform_responsiveness" else "pass",
                summary="x",
            )
            for name in REQUIRED_GATES
        ]
        assert qualification_verdict(gates) == verdict
    missing = [
        GateResult(gate_id=name, status="pass", summary="x")
        for name in REQUIRED_GATES
        if name != "reform_responsiveness"
    ]
    assert qualification_verdict(missing) == "incomplete"


@settings(max_examples=100, deadline=None)
@given(
    low=st.floats(min_value=-3.0, max_value=6.0),
    high=st.floats(min_value=-3.0, max_value=6.0),
)
def test_responsiveness_is_monotone_in_the_size_of_the_response(low, high):
    """Shrinking every response, or flipping its sign, never turns fail into pass."""

    low, high = sorted((low, high))
    order = {"fail": 0, "pass": 1}
    weaker = _responsiveness(_responsive_report(scale=low)).status
    stronger = _responsiveness(_responsive_report(scale=high)).status
    assert order[weaker] <= order[stronger]
    assert (weaker == "pass") == (low >= 1.0)
    assert (stronger == "pass") == (high >= 1.0)


REAL_REPORT = (
    Path(__file__).parent / "fixtures" / "uk_metrics" / "budget_metrics_report.json"
)


def _real_report():
    return json.loads(REAL_REPORT.read_text())


def test_the_real_report_on_the_certified_data_passes_responsiveness():
    """W3's real report: ten reforms, each clearing its minimum in every year."""

    report = _real_report()
    result, evidence = reform_responsiveness_gate(report)
    assert result.status == "pass", result.summary
    assert "All 10 standard reforms" in result.summary
    rows = {row["id"]: row for row in evidence["reforms"]}
    uc = rows["uc_standard_allowance_plus_10pc"]["target_changes"]
    pension = rows["state_pension_plus_10pc"]["target_changes"]
    assert all(3.0e9 < value < 3.4e9 for value in uc.values())
    assert all(12.3e9 < value < 14.5e9 for value in pension.values())


def reform_responsiveness_gate(report):
    from policyengine.provenance.uk_candidate import reform_responsiveness

    return reform_responsiveness(
        report=report, standard_reforms=_standard_reforms(), years=RESPONSE_YEARS
    )


@pytest.mark.parametrize("reform_id", [UC_ALLOWANCE, STATE_PENSION])
def test_the_backtest_failures_fail_on_the_real_report(reform_id):
    """Nikhil's backtest: UC allowance +10% returned exactly £0; State Pension +10% barely moved."""

    report = _real_report()
    for row in report["metrics"]:
        if row["metric_id"] == f"reform_targets.{reform_id}":
            row["value"] = 0.0 if reform_id == UC_ALLOWANCE else row["value"] * 0.01
    # The tool's own check would say fail; a report that still says pass is an error.
    assert reform_responsiveness_gate(report)[0].status == "error"
    for row in report["identities"]:
        if row["identity_id"] == f"responsive:{reform_id}":
            row["status"] = "fail"
            row["detail"] = "did not move"
    result = reform_responsiveness_gate(report)[0]
    assert result.status == "fail"
    assert f"({reform_id}) did not respond" in result.summary


def test_the_real_report_fits_the_metrics_review_classification():
    """Every check that fails on main is a no-worsening check, and every
    metric kind has a review bound, so a pair compared with itself passes."""

    from policyengine.provenance.uk_candidate import classify_check

    report = _real_report()
    bounds = json.loads(
        (
            Path(__file__).parents[1]
            / "src/policyengine/data/qualification/uk_review_bounds.json"
        ).read_text()
    )
    failing = sorted(
        row["identity_id"] for row in report["identities"] if row["status"] == "fail"
    )
    assert failing == [
        "counted_once:statutory_maternity_pay",
        "counted_once:statutory_sick_pay",
        "overlap_guard:property_transaction_tax_geography",
        "sign:vat",
    ]
    assert {classify_check(check_id) for check_id in failing} == {"regression"}
    assert {row["kind"] for row in report["metrics"]} <= set(bounds["kinds"])
    status, summary, evidence = compare_metric_reports(report, report, bounds)
    assert status == "pass", summary
    assert sorted(evidence["preexisting_check_failures"]) == failing
    # The same failures against a pair that passed them are regressions.
    clean = _real_report()
    for row in clean["identities"]:
        if row["status"] == "fail":
            row["status"] = "pass"
    assert compare_metric_reports(report, clean, bounds)[0] == "fail"


def test_a_real_failure_that_spread_to_a_new_year_has_worsened():
    """Scope-based no-worsening on the tool's real failing_scopes."""

    bounds = json.loads(
        (
            Path(__file__).parents[1]
            / "src/policyengine/data/qualification/uk_review_bounds.json"
        ).read_text()
    )
    report = _real_report()
    scopes = {
        row["identity_id"]: row["failing_scopes"]
        for row in report["identities"]
        if row["status"] == "fail"
    }
    assert scopes["sign:vat"] == [str(year) for year in RESPONSE_YEARS]
    assert scopes["counted_once:statutory_sick_pay"] == [""]
    # The previous pair failed sign:vat in every year but the last.
    earlier = _real_report()
    for row in earlier["identities"]:
        if row["identity_id"] == "sign:vat":
            row["failing_scopes"] = row["failing_scopes"][:-1]
    status, summary, _ = compare_metric_reports(report, earlier, bounds)
    assert status == "fail" and "sign:vat (fails in more scopes)" in summary
    # A candidate that fails it in fewer years than before has not worsened.
    assert compare_metric_reports(earlier, report, bounds)[0] == "pass"


def test_reform_checks_are_hard_in_the_metrics_review():
    from policyengine.provenance.uk_candidate import classify_check

    assert classify_check("reform_runs:basic_rate_plus_1pp") == "hard"
    assert classify_check("responsive:state_pension_plus_10pc") == "hard"


def test_metrics_with_nan_values_fail_rather_than_crash():
    nan = {**BASE, ("income_tax", 2027, "receipt"): float("nan")}
    result, evidence = metrics_review(
        candidate_report=_report(nan), previous_report=_report(BASE), bounds=BOUNDS
    )
    assert result.status == "fail"
    assert result.evidence_sha256
