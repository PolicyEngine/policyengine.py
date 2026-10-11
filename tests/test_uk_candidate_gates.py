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
from tests.qualification_fixtures import HARNESS, make_pair

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


def _importer(report=None, raises=None, missing=False):
    def runner(**kwargs):
        if raises:
            raise raises
        return report

    def importer(name):
        if missing:
            raise ModuleNotFoundError(name)
        return SimpleNamespace(run_budget_reform_contract=runner)

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


def _run_contract(report, *, versions=None, dataset_sha=CERTIFIED_SHA, **kwargs):
    kwargs.setdefault("seed", 0)
    kwargs.setdefault("max_examples", 20)
    kwargs.setdefault("dataset_path", Path("enhanced_frs_2024_25.h5"))
    return reform_contract(
        entrypoint=ENTRY,
        importer=_importer(report=report),
        expected_versions=versions
        or {"policyengine-uk": "2.126.8", "policyengine-core": "3.33.0"},
        expected_dataset_sha256=dataset_sha,
        **kwargs,
    )[0]


def test_w1_report_on_the_pinned_model_fails_on_its_defects():
    """W1's real report on policyengine-uk 2.125.1: 66 failures and 35 errors."""

    report = _fixture("pinned_uk_2.125.1_defects.json")
    result = _run_contract(
        report,
        versions={"policyengine-uk": "2.125.1", "policyengine-core": "3.33.0"},
        dataset_sha=None,
        dataset_path=None,
        max_examples=report["max_examples"],
    )
    assert result.status == "fail"
    assert result.summary.startswith("101 contract row(s) failed")
    assert result.details["problems"] == []


def test_w1_population_run_alone_is_incomplete():
    """W1's real population-only run has no cases and no sampled properties."""

    result = _run_contract(
        _fixture("population_pass_max_examples_0.json"), max_examples=0
    )
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


REPORT_TAMPERING = {
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
        "identities": extra.pop("identities", []),
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


REFORMS_FIXTURE = (
    Path(__file__).parent / "fixtures" / "uk_metrics" / "reforms_config.yaml"
)
REFORMS_PATH = "policyengine_uk/tests/microsimulation/reforms_config.yaml"


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
        files[f"{prefix}/policyengine_uk/tests/microsimulation/reforms_config.yaml"] = (
            REFORMS_FIXTURE.read_bytes()
        )
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
    assert _json.loads(settings)["reforms"] == []


def test_metrics_report_runner_passes_only_name_and_parameters(tmp_path):
    import json as _json

    from policyengine.provenance.uk_candidate import (
        METRICS_RUNNER,
        load_standard_reforms,
        run_metrics_report,
    )

    seen = {}

    def run(command, check, cwd):
        seen["settings"] = _json.loads(command[-2])
        Path(command[-1]).write_text(_json.dumps({"status": "ok"}))

    (tmp_path / "reforms_config.yaml").write_bytes(REFORMS_FIXTURE.read_bytes())
    reforms = load_standard_reforms(tmp_path, {})
    run_metrics_report(
        "python",
        tmp_path,
        years=[2029],
        out=tmp_path / "report.json",
        reforms=reforms,
        run=run,
    )
    assert len(seen["settings"]["reforms"]) == 8
    assert seen["settings"]["reforms"][0] == {
        "name": "Raise basic rate by 1pp",
        "parameters": {"gov.hmrc.income_tax.rates.uk[0].rate": 0.21},
    }
    # The runner hands the tool the reforms and reports the tool's own ids.
    assert "reforms=reforms" in METRICS_RUNNER
    assert 'report["reform_ids"]' in METRICS_RUNNER


def test_the_reform_list_is_vendored_with_the_tool(tmp_path):
    from policyengine.provenance.uk_candidate import (
        load_standard_reforms,
        vendor_metrics_tool,
    )

    tool = {
        "repository": "PolicyEngine/policyengine-uk",
        "commit": "c" * 40,
        "path": "policyengine_uk/utils/aggregate_impact",
        "reforms_path": REFORMS_PATH,
    }

    def get(url, timeout=None):
        return SimpleNamespace(content=_tool_tarball(), raise_for_status=lambda: None)

    root = vendor_metrics_tool(tool, tmp_path, get=get)
    reforms = load_standard_reforms(root, {})
    assert [reform["name"] for reform in reforms][:2] == [
        "Raise basic rate by 1pp",
        "Raise higher rate by 1pp",
    ]
    assert len(reforms) == 8
    missing = tmp_path / "missing"
    with pytest.raises(ValueError, match="reforms_config.yaml"):
        vendor_metrics_tool(
            tool,
            missing,
            get=lambda url, timeout=None: SimpleNamespace(
                content=_tool_tarball(include_reforms=False),
                raise_for_status=lambda: None,
            ),
        )


def test_a_standard_reform_has_one_definition(tmp_path):
    from policyengine.provenance.uk_candidate import load_standard_reforms

    (tmp_path / "reforms_config.yaml").write_bytes(REFORMS_FIXTURE.read_bytes())
    extra = {
        "name": "Raise the State Pension by 10%",
        "parameters": {"gov.dwp.state_pension.new_state_pension.amount": 253.3},
        "expected_impact": -12.0,
    }
    reforms = load_standard_reforms(tmp_path, {"additional_reforms": [extra]})
    assert len(reforms) == 9 and reforms[-1]["name"] == extra["name"]
    with pytest.raises(ValueError, match="defined twice"):
        load_standard_reforms(
            tmp_path,
            {"additional_reforms": [{**extra, "name": "Raise basic rate by 1pp"}]},
        )
    assert load_standard_reforms(None, {}) == []


# --- Reform responsiveness -----------------------------------------------------------

RESPONSE_YEARS = [2025, 2026, 2027, 2028, 2029, 2030, 2031]


def _standard_reforms():
    import yaml

    return yaml.safe_load(REFORMS_FIXTURE.read_text())["reforms"]


def _slug(name):
    import re

    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _responsive_report(scale=1.0, overrides=None, years=RESPONSE_YEARS):
    """A report in which each reform moves the balance by scale x its expected impact."""

    overrides = overrides or {}
    metrics, identities, ids = [], [], {}
    for reform in _standard_reforms():
        reform_id = _slug(reform["name"])
        ids[reform["name"]] = reform_id
        identities.append({"identity_id": f"reform_runs:{reform_id}", "status": "pass"})
        for year in years:
            value = overrides.get(
                (reform_id, year), reform["expected_impact"] * 1e9 * scale
            )
            if value is not None:
                metrics.append(
                    {
                        "metric_id": f"reforms.{reform_id}",
                        "year": year,
                        "value": value,
                        "kind": "reform",
                    }
                )
    return {
        "status": "ok",
        "metrics": metrics,
        "identities": identities,
        "reform_ids": ids,
    }


def _responsiveness(report, reforms=None, **kwargs):
    from policyengine.provenance.uk_candidate import reform_responsiveness

    kwargs.setdefault("years", RESPONSE_YEARS)
    kwargs.setdefault("reference_year", 2029)
    kwargs.setdefault("floor_gbp", 1e8)
    kwargs.setdefault("min_share_of_expected", 0.25)
    return reform_responsiveness(
        report=report,
        standard_reforms=_standard_reforms() if reforms is None else reforms,
        **kwargs,
    )[0]


def test_reforms_that_respond_as_recorded_pass():
    result = _responsiveness(_responsive_report())
    assert result.status == "pass", result.summary
    assert "All 8 standard reforms" in result.summary
    assert "2025-26 to 2031-32" in result.summary


UC_TAPER = "reduce_universal_credit_taper_rate_to_20"
BASIC_RATE = "raise_basic_rate_by_1pp"


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        (
            {(UC_TAPER, 2027): 0.0},
            "moved the balance by £0 in 2027-28; expected a cost",
        ),
        ({(UC_TAPER, 2027): -4.0e7}, "by only £-40,000,000 in 2027-28"),
        ({(BASIC_RATE, 2026): -7.1e9}, "expected a gain"),
        ({(BASIC_RATE, 2029): 1.0e9}, "under 25% of the expected £7.1bn"),
        ({(BASIC_RATE, 2030): None}, "has no costing for 2030-31"),
        ({(BASIC_RATE, 2030): float("nan")}, "has no costing for 2030-31"),
    ],
    ids=[
        "exactly zero",
        "nearly inert",
        "wrong sign",
        "small at reference",
        "missing",
        "nan",
    ],
)
def test_a_reform_that_does_not_respond_fails_qualification(overrides, fragment):
    """The backtest's two modes (exactly £0, nearly inert) and their neighbours."""

    result = _responsiveness(_responsive_report(overrides=overrides))
    assert result.status == "fail"
    assert fragment in result.summary, result.summary


def test_a_reform_that_did_not_run_fails():
    report = _responsive_report()
    for row in report["identities"]:
        if row["identity_id"] == f"reform_runs:{UC_TAPER}":
            row["status"] = "fail"
    assert "did not run to completion" in _responsiveness(report).summary
    report = _responsive_report()
    del report["reform_ids"]["Raise VAT standard rate by 2pp"]
    result = _responsiveness(report)
    assert result.status == "fail" and "was not run" in result.summary


def test_responsiveness_is_never_skipped_or_guessed():
    assert _responsiveness(None).status == "unavailable"
    assert _responsiveness(_responsive_report(), reforms=[]).status == "unavailable"
    assert _responsiveness(_responsive_report(), reference_year=2040).status == "error"
    unsigned = [{**_standard_reforms()[0], "expected_impact": 0}]
    assert _responsiveness(_responsive_report(), reforms=unsigned).status == "error"
    assert qualification_verdict_for("reform_responsiveness", "unavailable") == (
        "incomplete"
    )
    assert qualification_verdict_for("reform_responsiveness", "fail") == "rejected"


def qualification_verdict_for(gate_id, status):
    from policyengine.provenance.qualification import (
        REQUIRED_GATES,
        GateResult,
        qualification_verdict,
    )

    assert gate_id in REQUIRED_GATES
    return qualification_verdict(
        GateResult(
            gate_id=name, status=status if name == gate_id else "pass", summary="x"
        )
        for name in REQUIRED_GATES
    )


@settings(max_examples=100, deadline=None)
@given(
    low=st.floats(min_value=-2.0, max_value=3.0),
    high=st.floats(min_value=-2.0, max_value=3.0),
)
def test_responsiveness_is_monotone_in_the_size_of_the_response(low, high):
    """Shrinking every response, or flipping its sign, never turns fail into pass."""

    low, high = sorted((low, high))
    order = {"fail": 0, "pass": 1}
    weaker = _responsiveness(_responsive_report(scale=low)).status
    stronger = _responsiveness(_responsive_report(scale=high)).status
    assert order[weaker] <= order[stronger]
    if low <= 0:
        assert weaker == "fail"
    if high >= 0.25:
        assert stronger == "pass"


def test_metrics_with_nan_values_fail_rather_than_crash():
    nan = {**BASE, ("income_tax", 2027, "receipt"): float("nan")}
    result, evidence = metrics_review(
        candidate_report=_report(nan), previous_report=_report(BASE), bounds=BOUNDS
    )
    assert result.status == "fail"
    assert result.evidence_sha256
