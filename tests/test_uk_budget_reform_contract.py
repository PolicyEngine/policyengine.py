"""The UK Budget reform contract runner.

The runner's oracles, representations and status logic are tested here
without depending on which policyengine-uk is installed. Whether an
installed model satisfies the contract is what qualification checks; the
integration test at the end runs one case when the installed
policyengine-uk has the statutory-timeline reform routes.
"""

import datetime
import json

import pytest

pytest.importorskip("policyengine_uk")

from policyengine.tax_benefit_models.uk import budget_reform_contract as contract
from policyengine.tax_benefit_models.uk.budget_reform_contract import (
    CASES,
    Case,
    Change,
    Check,
    RouteRun,
    adult,
    country_reform_dict,
    evaluate_case,
    expected_annual,
    fiscal_year_average,
    run_budget_reform_contract,
    s21_basic_rate_limit,
    s57_personal_allowance,
    weekly,
    wrapper_reform_dict,
)

RATE = "gov.hmrc.income_tax.rates.uk[0].rate"


# Oracles.


def test_statutory_indexation_arithmetic():
    # ITA 2007 s57(3): 12,570 x 5% = 628.50, rounded up to 630.
    assert s57_personal_allowance(12_570, 0.05) == 13_200
    # s21(3): 37,700 x 1.05 = 39,585, rounded up to 39,600.
    assert s21_basic_rate_limit(37_700, 0.05) == 39_600
    # No rise without a CPI increase (s57(2), s21(1)).
    assert s57_personal_allowance(12_570, 0) == 12_570
    assert s21_basic_rate_limit(37_700, -0.01) == 37_700
    # A rise that is already a multiple of £10 is not rounded further.
    assert s57_personal_allowance(10_000, 0.02) == 10_200


def test_weekly_thresholds_round_to_the_penny():
    assert weekly(12_570) == 241.73
    assert weekly(50_270) == 966.73


def test_fiscal_year_average_is_day_weighted():
    pieces = [
        (datetime.date(2024, 10, 30), 0.18),
        (datetime.date(2027, 10, 30), 0.20),
    ]
    # 6 April to 29 October 2027 is 207 days; 2027-28 has 366.
    assert fiscal_year_average(pieces, 2027) == pytest.approx(
        (0.18 * 207 + 0.20 * 159) / 366, abs=1e-12
    )
    assert fiscal_year_average(pieces, 2028) == pytest.approx(0.20)


def test_expected_annual_for_a_single_change():
    def baseline(path, year):
        return 0.20

    april = Change(RATE, datetime.date(2027, 4, 6), 0.21)
    finite = Change(RATE, datetime.date(2027, 4, 6), 0.21, datetime.date(2028, 4, 5))
    may = Change(RATE, datetime.date(2027, 5, 1), 0.21)
    assert [expected_annual(april, y, baseline) for y in (2026, 2027, 2028)] == [
        0.20,
        0.21,
        0.21,
    ]
    assert [expected_annual(finite, y, baseline) for y in (2027, 2028)] == [0.21, 0.20]
    # A change after 30 April misses that fiscal year's sample.
    assert expected_annual(may, 2027, baseline) == 0.20


# Representations.


def test_representations():
    changes = (
        Change(RATE, datetime.date(2027, 4, 6), 0.21, datetime.date(2028, 4, 5)),
        Change(RATE, datetime.date(2028, 4, 6), 0.22),
    )
    assert country_reform_dict(changes) == {
        RATE: {"2027-04-06.2028-04-05": 0.21, "2028-04-06.2100-12-31": 0.22}
    }
    assert wrapper_reform_dict(changes) == {
        RATE: {"2027-04-06.2028-04-05": 0.21, "2028-04-06": 0.22}
    }


def test_case_ids_are_unique_and_every_check_has_an_oracle():
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids))
    for case in CASES:
        for check in case.checks:
            assert check.oracle, (case.id, check)
            assert check.target in {
                "parameter",
                "variable",
                "change",
                "baseline_equals",
            }
        assert case.changes or case.representations, case.id


# Status logic, through a fake route.


class FakeRoute:
    def __init__(self, reformed, unreformed, isolation=(), error=None, after=()):
        self.reformed, self.unreformed = reformed, unreformed
        self.isolation, self.error = list(isolation), error
        self.after = list(after)

    def run(self, case, representation, cache):
        if self.error is not None:
            raise self.error
        run = RouteRun()
        run.reformed.update(self.reformed)
        run.unreformed.update(self.unreformed)
        run.isolation.extend(self.isolation)
        run.after.extend(self.after)
        return run


def fake(monkeypatch, route):
    monkeypatch.setattr(contract, "_route", lambda name: route)
    monkeypatch.setattr(
        contract, "_baseline_parameter_reader", lambda: lambda p, y: 0.20
    )


CASE = Case(
    id="fake",
    title="fake",
    changes=(Change(RATE, datetime.date(2027, 4, 6), 0.21),),
    household=adult(),
    checks=(
        Check("parameter", RATE, 2027, 0.21, "oracle"),
        Check("change", "income_tax", 2027, 174.30, "oracle", 0.005),
        Check("variable", "income_tax", 2027, 0.0, "oracle", pending="d1344"),
    ),
)


def test_passing_failing_pending_and_isolation_rows(monkeypatch):
    fake(
        monkeypatch,
        FakeRoute(
            reformed={
                ("parameter", RATE, 2027): 0.21,
                ("variable", "income_tax", 2027): 3_660.30,
            },
            unreformed={("variable", "income_tax", 2027): 3_486.00},
            isolation=[("income_tax", 2027, 3_486.0, 3_486.0)],
        ),
    )
    rows = {row["check"]: row for row in evaluate_case(CASE, "country.reform_dict")}
    assert rows[f"parameter:{RATE}:2027"]["status"] == "pass"
    assert rows["change:income_tax:2027"]["status"] == "pass"
    assert rows["variable:income_tax:2027"]["status"] == "pending"
    assert rows["variable:income_tax:2027"]["decision_id"] == "d1344"
    assert rows["variable:income_tax:2027"]["holds"] is False
    assert rows["baseline_isolation:income_tax:2027"]["status"] == "pass"


@pytest.mark.parametrize("route", ["country.reform_dict", "wrapper.household"])
def test_assertions_with_the_same_value_request_have_distinct_identities(
    monkeypatch, route
):
    from dataclasses import replace

    duplicate = replace(
        CASE,
        checks=(
            Check("parameter", RATE, 2027, 0.21, "mandatory oracle"),
            Check("parameter", RATE, 2027, 0.20, "pending oracle", pending="d1344"),
        ),
    )
    fake(
        monkeypatch,
        FakeRoute(reformed={("parameter", RATE, 2027): 0.21}, unreformed={}),
    )
    rows = evaluate_case(duplicate, route)
    assert [row["status"] for row in rows] == (
        ["pass", "pending"]
        if route == "country.reform_dict"
        else ["unsupported", "unsupported"]
    )
    assert len({row["check"] for row in rows}) == 1
    assert all(
        isinstance(row["assertion_id"], str) and row["assertion_id"] for row in rows
    )
    assert len({row["assertion_id"] for row in rows}) == 2


def test_assertion_ids_change_no_verdict():
    """Labelling rows changes no status, expected value or actual value.

    The fixture holds the rows the runner produced on main 503d4998, before
    rows carried an ``assertion_id``, for every case and route under fixed
    fake routes plus focused verdict scenarios (see
    ``tests/uk_contract_row_scenarios.py``).
    """

    from pathlib import Path

    from tests.uk_contract_row_scenarios import scenario_rows

    fixture = Path(__file__).parent / "fixtures/uk_contract/evaluate_case_rows.json"
    assert scenario_rows(contract, CASES) == json.loads(fixture.read_text())


def test_a_wrong_value_fails_and_a_leaking_baseline_fails(monkeypatch):
    fake(
        monkeypatch,
        FakeRoute(
            reformed={
                ("parameter", RATE, 2027): 0.20,
                ("variable", "income_tax", 2027): 3_486.00,
            },
            unreformed={("variable", "income_tax", 2027): 3_486.00},
            isolation=[("income_tax", 2027, 3_660.3, 3_486.0)],
        ),
    )
    rows = {row["check"]: row for row in evaluate_case(CASE, "country.reform_dict")}
    assert rows[f"parameter:{RATE}:2027"]["status"] == "fail"
    assert rows["change:income_tax:2027"]["status"] == "fail"
    assert rows["baseline_isolation:income_tax:2027"]["status"] == "fail"


def test_a_crash_is_an_error_and_parameters_are_unsupported_on_wrapper_routes(
    monkeypatch,
):
    fake(monkeypatch, FakeRoute({}, {}, error=RuntimeError("boom")))
    (row,) = evaluate_case(CASE, "country.reform_dict")
    assert row["status"] == "error" and "boom" in row["detail"]
    fake(
        monkeypatch,
        FakeRoute(
            reformed={("variable", "income_tax", 2027): 3_660.30},
            unreformed={("variable", "income_tax", 2027): 3_486.00},
        ),
    )
    rows = {row["check"]: row for row in evaluate_case(CASE, "wrapper.household")}
    assert rows[f"parameter:{RATE}:2027"]["status"] == "unsupported"
    assert rows["change:income_tax:2027"]["status"] == "pass"


def test_rejection_cases(monkeypatch):
    case = next(case for case in CASES if case.id == "unknown_path")
    fake(monkeypatch, FakeRoute({}, {}, error=ValueError("no new_credit here")))
    (row,) = evaluate_case(case, "country.reform_dict")
    assert row["status"] == "pass"
    fake(monkeypatch, FakeRoute({}, {}, error=ValueError("something else")))
    (row,) = evaluate_case(case, "country.reform_dict")
    assert row["status"] == "fail"
    fake(monkeypatch, FakeRoute({}, {}))
    (row,) = evaluate_case(case, "country.reform_dict")
    assert row["status"] == "fail" and row["actual"] == "accepted"


def test_report_shape_for_an_unsupported_route():
    report = run_budget_reform_contract(routes=["api.sim_api"], max_examples=0)
    json.dumps(report)
    assert report["contract_id"] == contract.CONTRACT_ID
    assert report["contract_version"] == contract.CONTRACT_VERSION
    assert report["prior_law_option"] == "projected"
    unsupported = [row for row in report["cases"] if row["case_id"] != "run"]
    assert {row["status"] for row in unsupported} == {"unsupported"}
    assert all(row["reason"] for row in unsupported)
    # Nothing passed, so the run certifies nothing.
    (run,) = [row for row in report["cases"] if row["case_id"] == "run"]
    assert run["status"] == "error"
    assert report["summary"]["error"] == 1
    assert report["holds"] is False


@pytest.mark.parametrize(
    "selection, message",
    [
        ({"routes": ["country.typo"]}, "Unknown routes"),
        ({"routes": []}, "No routes"),
        ({"cases": ["april_rate_chagne"]}, "Unknown cases"),
        ({"cases": []}, "No cases"),
    ],
)
def test_a_selection_that_would_certify_nothing_is_rejected(selection, message):
    with pytest.raises(ValueError, match=message):
        run_budget_reform_contract(max_examples=0, **selection)


def test_an_unreformed_run_that_moves_after_the_reform_fails(monkeypatch):
    fake(
        monkeypatch,
        FakeRoute(
            reformed={("variable", "income_tax", 2027): 3_660.30},
            unreformed={("variable", "income_tax", 2027): 3_486.00},
            after=[("income_tax", 2027, 3_660.30, 3_486.00)],
        ),
    )
    rows = {row["check"]: row for row in evaluate_case(CASE, "wrapper.household")}
    assert rows["change:income_tax:2027"]["status"] == "pass"
    assert rows["unreformed_after_reform:income_tax:2027"]["status"] == "fail"


def test_expected_values_read_the_reference_they_are_given(monkeypatch):
    fake(
        monkeypatch,
        FakeRoute(
            reformed={("variable", "income_tax", 2027): 3_660.30},
            unreformed={("variable", "income_tax", 2027): 3_486.00},
        ),
    )
    case = next(case for case in CASES if case.id == "april_rate_change")
    # A reference that a leak had moved to 21% would expect no change.
    rows = evaluate_case(case, "wrapper.household", reference=lambda path, year: 0.21)
    (row,) = [row for row in rows if row["check"] == "change:income_tax:2027"]
    assert row["status"] == "fail" and row["expected"] == 0.0


def test_module_parameters_unchanged_compares_the_shared_state():
    before = contract.shared_state()
    assert "system" in before
    assert contract.module_parameters_unchanged(before)["status"] == "pass"
    # Changing the snapshot (never the shared state) stands in for a leak.
    tree = "processed" if "processed" in before else "system"
    entries, metadata = before[tree][RATE][0]
    # A change on one date, 6 April 2027, that no 1 January reading sees.
    before[tree][RATE][0] = (entries + (("2027-04-06", 0.5),), metadata)
    row = contract.module_parameters_unchanged(before)
    assert row["status"] == "fail" and f"{tree}:{RATE}" in row["actual"]


def test_module_parameters_unchanged_compares_projected_timelines():
    before = contract.shared_state()
    if "projected" not in before:
        pytest.skip("this policyengine-uk keeps no projected timelines")
    name = next(iter(before["projected"]))
    before["projected"][name] = before["projected"][name][1:]
    row = contract.module_parameters_unchanged(before)
    assert row["status"] == "fail" and f"projected:{name}" in row["actual"]


def test_a_run_in_which_nothing_passed_errors_with_an_in_process_route():
    # A country-only case selected with a wrapper route runs nothing; the
    # run-level parameters row passes, but must not count as a pass.
    report = run_budget_reform_contract(
        routes=["wrapper.household"],
        cases=["september_cpi_moves_indexed_thresholds"],
        max_examples=0,
    )
    statuses = {row["case_id"]: row["status"] for row in report["cases"]}
    assert statuses == {"module_parameters_unchanged": "pass", "run": "error"}
    assert report["holds"] is False


def _failing_property(monkeypatch, error):
    def check(change, income, routes, cache, reference):
        raise error

    monkeypatch.setattr(contract, "_property_routes_agree", check)
    return contract.run_property(
        "routes_agree_and_baselines_hold",
        ["country.reform_dict", "wrapper.household"],
        seed=0,
        max_examples=3,
        cache={},
        reference=lambda path, year: 0.20,
    )


def _without_hypothesis(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name == "hypothesis" or name.startswith("hypothesis."):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.mark.parametrize("hypothesis_installed", [True, False])
@pytest.mark.parametrize(
    "error, status",
    [(AssertionError("routes disagree"), "fail"), (RuntimeError("crashed"), "error")],
)
def test_both_property_engines_report_failures_with_their_inputs(
    monkeypatch, hypothesis_installed, error, status
):
    if hypothesis_installed:
        pytest.importorskip("hypothesis")
    else:
        _without_hypothesis(monkeypatch)
    result = _failing_property(monkeypatch, error)
    assert result["status"] == status
    assert result["engine"] == ("hypothesis" if hypothesis_installed else "random")
    counterexample = result["counterexample"]
    assert counterexample["change"].startswith("Change(")
    assert isinstance(counterexample["income"], int)
    assert str(error) in counterexample["detail"]


# Integration: one case on the installed model.


def test_the_april_rate_case_holds_on_the_country_routes():
    pytest.importorskip("policyengine_uk.utils.dated_reforms")
    report = run_budget_reform_contract(
        routes=list(contract.COUNTRY_ROUTES),
        cases=["april_rate_change", "finite_rate_change"],
        max_examples=0,
    )
    failures = [row for row in report["cases"] if row["status"] in ("fail", "error")]
    assert failures == []
    checks = [row["check"] for row in report["cases"] if row["route"] != "all"]
    assert "unreformed_after_reform:income_tax:2027" in checks
    # Each value is checked once per case and route.
    labelled = [(row["case_id"], row["route"], row["check"]) for row in report["cases"]]
    assert len(labelled) == len(set(labelled))
    assert any(
        row["case_id"] == "module_parameters_unchanged" for row in report["cases"]
    )


def test_a_parameter_modifier_writes_the_annualised_parameters():
    from policyengine_uk import Simulation

    simulation = Simulation(situation=contract._situation(adult(), [2027]))
    contract.parameter_modifier(
        [
            Change(RATE, datetime.date(2027, 1, 1), 0.25, datetime.date(2027, 12, 31)),
            Change(
                "gov.hmrc.income_tax.rates.dividends[0].rate",
                datetime.date(2026, 1, 1),
                0.0875,
            ),
        ]
    )(simulation)
    parameters = simulation.tax_benefit_system.parameters
    assert parameters.get_child(RATE)("2027-01-01") == 0.25
    assert parameters.get_child(RATE)("2028-01-01") == 0.20
    dividends = parameters.get_child("gov.hmrc.income_tax.rates.dividends[0].rate")
    assert dividends("2030-01-01") == 0.0875


def test_modifier_cases_differ_only_in_order_and_skip_the_household_route():
    first, second = (
        next(case for case in CASES if case.id == case_id)
        for case_id in (
            "modifier_then_parameter_changes",
            "parameter_changes_then_modifier",
        )
    )
    assert first.modifier and first.modifier == second.modifier
    assert first.changes == second.changes
    assert first.modifier_first and not second.modifier_first
    assert "wrapper.household" not in first.routes
    assert contract.reform_digest({}, "wrapper.policy", first) != (
        contract.reform_digest({}, "wrapper.policy", second)
    )
    # Cases without a modifier keep their digests.
    plain = next(case for case in CASES if case.id == "april_rate_change")
    assert contract.reform_digest({}, "r", plain) == contract.reform_digest({}, "r")


# Population checks.


@pytest.fixture
def stub_population_checks(monkeypatch):
    """Run every population branch with deterministic, responsive fake arrays."""
    from types import SimpleNamespace

    import policyengine_uk
    from policyengine_core.reforms import Reform
    from policyengine_uk.utils import scenario

    from policyengine.tax_benefit_models.uk import (
        budget_reform_population as population,
    )

    class Simulation:
        def __init__(self, dataset, reform=None, scenario=None):
            self.reform = reform if scenario is None else scenario.parameter_changes

        @property
        def baseline(self):
            return Simulation(dataset=None)

        def calculate(self, variable, year):
            if (
                variable == "income_tax"
                and year == 2027
                and self.reform in (population.APRIL, population.FINITE)
            ):
                return [2.0]
            if self.reform == {"response": population.UC_STANDARD_ALLOWANCES}:
                if variable in ("uc_standard_allowance", "universal_credit"):
                    return [1.1]
            if self.reform == {"response": population.STATE_PENSION_RATES}:
                if variable in (
                    "basic_state_pension",
                    "new_state_pension",
                    "state_pension",
                ):
                    return [1.1]
            return [1.0]

    monkeypatch.setattr(policyengine_uk, "Microsimulation", Simulation)
    monkeypatch.setattr(
        scenario, "Scenario", lambda **kwargs: SimpleNamespace(**kwargs)
    )
    monkeypatch.setattr(
        Reform, "from_dict", staticmethod(lambda reform, **kwargs: reform)
    )
    monkeypatch.setattr(
        population, "subsample", lambda *args: SimpleNamespace(copy=lambda: None)
    )
    monkeypatch.setattr(
        population, "plus_ten_percent", lambda paths: {"response": paths}
    )
    return population


@pytest.mark.parametrize("failure", ["early", "partial"])
def test_population_errors_emit_only_the_declared_diagnostic_after_progress(
    monkeypatch, stub_population_checks, failure
):
    population = stub_population_checks
    route = "country.reform_dict"

    def fail(*args):
        raise OSError("forced population failure")

    monkeypatch.setattr(
        population, "subsample" if failure == "early" else "plus_ten_percent", fail
    )
    rows = population.run_population_checks("unused.h5", [route], seed=7)
    diagnostic = {
        "check_id": population.POPULATION_ERROR_DIAGNOSTIC[0],
        "route": population.POPULATION_ERROR_DIAGNOSTIC[1],
        "status": "error",
        "detail": "OSError: forced population failure",
        "subsample_households": population.SUBSAMPLE_HOUSEHOLDS,
        "seed": 7,
    }
    assert population.POPULATION_ERROR_DIAGNOSTIC == ("population", "-")
    assert population.POPULATION_ERROR_DIAGNOSTIC not in (
        population.population_check_routes([route])
    )
    expected_progress = (
        []
        if failure == "early"
        else [
            (population.POPULATION_BASELINE_ISOLATION, route),
            (population.POPULATION_BASELINE_ISOLATION, "unreformed"),
            (population.POPULATION_QUERY_ORDER, "unreformed"),
            (population.POPULATION_APRIL_RATE_CHANGE, route),
            (population.POPULATION_FINITE_CHANGE_EXPIRES, route),
        ]
    )
    assert rows[-1] == diagnostic
    assert [(row["check_id"], row["route"]) for row in rows[:-1]] == expected_progress
    assert all(row["status"] == "pass" for row in rows[:-1])
    assert [row for row in rows if row["status"] == "error"] == [diagnostic]


def test_a_report_with_the_population_error_diagnostic_does_not_hold(
    monkeypatch, stub_population_checks
):
    population = stub_population_checks
    diagnostic = {
        "check_id": population.POPULATION_ERROR_DIAGNOSTIC[0],
        "route": population.POPULATION_ERROR_DIAGNOSTIC[1],
        "status": "error",
        "detail": "forced population failure",
    }
    monkeypatch.setattr(population, "run_population_checks", lambda *args: [diagnostic])
    monkeypatch.setattr(contract, "evaluate_case", lambda *args: [{"status": "pass"}])
    monkeypatch.setattr(contract, "release_dead_variable_modules", lambda: None)
    monkeypatch.setattr(contract, "PROPERTIES", ())
    monkeypatch.setattr(contract, "reference_parameters", lambda: None)
    monkeypatch.setattr(contract, "parameter_reader", lambda parameters: None)
    monkeypatch.setattr(contract, "shared_state", lambda: {})
    monkeypatch.setattr(
        contract, "module_parameters_unchanged", lambda before: {"status": "pass"}
    )
    monkeypatch.setattr(contract, "_sha256", lambda path: "unused")
    report = run_budget_reform_contract(
        routes=["country.reform_dict"],
        cases=["april_rate_change"],
        dataset_path="unused.h5",
        max_examples=0,
    )
    assert report["population"] == [diagnostic]
    assert report["summary"]["error"] == 1
    assert report["holds"] is False


@pytest.mark.parametrize(
    "routes",
    [
        ["country.reform_dict", "country.reform_dict"],
        ["country.reform_dict", "country.scenario_parameter_changes"],
        [
            "country.reform_dict",
            "country.scenario_parameter_changes",
            "country.reform_dict",
            "country.reform_from_dict",
        ],
    ],
)
def test_population_coverage_deduplicates_only_country_baseline_rows(
    stub_population_checks, routes
):
    from collections import Counter

    population = stub_population_checks
    rows = population.run_population_checks("unused.h5", routes)
    declared = Counter(population.population_check_routes(routes))
    assert rows and all(row["status"] == "pass" for row in rows), rows
    assert Counter((row["check_id"], row["route"]) for row in rows) == declared
    route_counts = Counter(routes)
    for route, count in route_counts.items():
        assert declared[(population.POPULATION_BASELINE_ISOLATION, route)] == 1
        for check in population.COUNTRY_POPULATION_CHECKS[1:]:
            assert declared[(check, route)] == count
    assert (
        sum(
            count
            for (check, route), count in declared.items()
            if check == population.POPULATION_ROUTES_AGREE
        )
        == len(routes) - 1
    )


def _tiny_dataset_file(tmp_path, households=5, recipients=False):
    """Earners on £10,000 to £50,000, one household each.

    With ``recipients``, two more households: a pensioner above the full
    State Pension and a working-age adult with no income, who claims
    Universal Credit, so the responsiveness checks have awards to move.
    """
    import pandas as pd
    from policyengine_uk.data import UKSingleYearDataset

    ages = [40] * households
    earnings = [10_000.0 * i for i in range(1, households + 1)]
    pensions = [0.0] * households
    if recipients:
        ages += [70, 30]
        earnings += [0.0, 0.0]
        pensions += [20_000.0, 0.0]
        households += 2
    ids = list(range(1, households + 1))
    person = pd.DataFrame(
        {
            "person_id": ids,
            "person_benunit_id": ids,
            "person_household_id": ids,
            "age": ages,
            "employment_income": earnings,
            "state_pension_reported": pensions,
            "person_weight": [1.0] * households,
        }
    )
    benunit = pd.DataFrame({"benunit_id": ids, "benunit_weight": [1.0] * households})
    household = pd.DataFrame(
        {
            "household_id": ids,
            "household_weight": [1.0] * households,
            "region": ["LONDON"] * households,
            "tenure_type": ["OWNED_OUTRIGHT"] * households,
            "council_tax": [0.0] * households,
            "rent": [0.0] * households,
        }
    )
    path = tmp_path / "tiny.h5"
    UKSingleYearDataset(
        person=person, benunit=benunit, household=household, fiscal_year=2025
    ).save(str(path))
    return str(path)


def test_the_subsample_is_deterministic_and_keeps_whole_households(tmp_path):
    from policyengine.tax_benefit_models.uk.budget_reform_population import subsample

    path = _tiny_dataset_file(tmp_path, households=5)
    first = subsample(path, 3, seed=7)
    again = subsample(path, 3, seed=7)
    kept = sorted(first.household["household_id"])
    assert kept == sorted(again.household["household_id"])
    assert len(kept) == 3
    assert set(first.person["person_household_id"]) == set(kept)
    assert set(first.benunit["benunit_id"]) == set(first.person["person_benunit_id"])
    everything = subsample(path, 50, seed=7)
    assert len(everything.household) == 5


def test_population_checks_hold_on_a_tiny_dataset(tmp_path):
    pytest.importorskip("policyengine_uk.utils.dated_reforms")
    from policyengine.tax_benefit_models.uk.budget_reform_population import (
        population_check_routes,
        run_population_checks,
    )

    rows = run_population_checks(
        _tiny_dataset_file(tmp_path, recipients=True),
        list(contract.COUNTRY_ROUTES),
        seed=0,
    )
    assert rows and all(row["status"] == "pass" for row in rows), rows
    from collections import Counter

    assert Counter((row["check_id"], row["route"]) for row in rows) == Counter(
        population_check_routes(list(contract.COUNTRY_ROUTES))
    )


def test_responsiveness_checks_fail_with_no_award_to_move(tmp_path):
    pytest.importorskip("policyengine_uk.utils.dated_reforms")
    from policyengine.tax_benefit_models.uk.budget_reform_population import (
        run_population_checks,
    )

    rows = run_population_checks(
        _tiny_dataset_file(tmp_path), ["country.reform_dict"], seed=0
    )
    status = {row["check_id"]: row["status"] for row in rows}
    # Earners only: no award to show a reform reaching it.
    assert status["population_state_pension_plus_10"] == "fail"
    assert status["population_april_rate_change"] == "pass"


def test_expected_annual_for_a_blended_change_that_started_earlier():
    def baseline(path, year):
        return 0.18

    cgt = "gov.hmrc.cgt.basic_rate"
    earlier = Change(cgt, datetime.date(2025, 6, 1), 0.20)
    assert expected_annual(earlier, 2026, baseline) == pytest.approx(0.20)
    ends = Change(cgt, datetime.date(2025, 6, 1), 0.20, datetime.date(2026, 10, 29))
    # 6 April to 29 October 2026 is 207 days of 365.
    assert expected_annual(ends, 2026, baseline) == pytest.approx(
        (0.20 * 207 + 0.18 * 158) / 365
    )


def test_the_subsample_reads_a_file_without_an_h5_extension(tmp_path):
    import shutil

    from policyengine.tax_benefit_models.uk.budget_reform_population import subsample

    blob = tmp_path / "6a842565bc10"
    shutil.copy(_tiny_dataset_file(tmp_path), blob)
    assert len(subsample(str(blob), 3, seed=7).household) == 3


def test_household_result_totals_read_each_variable_from_its_own_entity():
    from policyengine.tax_benefit_models.uk.budget_reform_contract import (
        _result_total,
    )

    # universal_credit is a benefit-unit variable; the household result can
    # also carry it aggregated to the household.
    result = {
        "person": [{"income_tax": 100.0}, {"income_tax": 50.0}],
        "benunit": {"universal_credit": 6_000.0},
        "household": {"universal_credit": 6_000.0},
    }
    assert _result_total(result, "universal_credit") == 6_000.0
    assert _result_total(result, "income_tax") == 150.0
    with pytest.raises(KeyError, match="benunit"):
        _result_total({"household": {"universal_credit": 1.0}}, "universal_credit")
