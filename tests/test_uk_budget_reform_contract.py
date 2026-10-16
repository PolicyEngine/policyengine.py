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


def test_the_response_oracle_is_the_static_one_at_an_elasticity_of_zero():
    current_law = {
        contract.CGT_ANNUAL_EXEMPT_AMOUNT: 3_000.0,
        contract.CGT_BASIC_RATE: 0.18,
    }
    context = contract.Context(lambda path, year: current_law[path])
    # (£10,000 - £3,000) x (20% - 18%).
    assert contract._gains_uplift(2027, 1.0)(context) == pytest.approx(140.0)
    assert contract._gains_response_uplift(2027, 0.20, 0.0)(context) == (
        pytest.approx(140.0)
    )
    # At an elasticity of 1 the gains scale by (1 - 20%) / (1 - 18%).
    realised = 10_000 * 0.8 / 0.82
    assert contract._realised_gains(2027, 0.20, 1.0)(context) == pytest.approx(realised)
    assert contract._gains_response_uplift(2027, 0.20, 1.0)(context) == (
        pytest.approx((realised - 3_000) * 0.20 - 7_000 * 0.18)
    )


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


def test_the_rate_blending_case_holds_realisations_fixed_on_every_route():
    case = next(case for case in CASES if case.id == "mid_year_blended_rate")
    static = {
        contract.CGT_ELASTICITY: [0.0],
        contract.CGT_MTR_ELASTICITY: [0.0],
        contract.CGT_SEPARATE_BADR_ELASTICITY: [False],
    }
    for route in contract.COUNTRY_ROUTES + contract.WRAPPER_ROUTES:
        reform = contract.represent(case, route)
        assert {path: list(reform[path].values()) for path in static} == static


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


def _fake_shared_tree(monkeypatch, data):
    from policyengine_core.parameters import ParameterNode

    tree = ParameterNode("", data=data)
    monkeypatch.setattr(contract, "_shared_trees", lambda: {"system": tree})
    return tree


def test_a_list_value_changed_in_place_is_caught(monkeypatch):
    tree = _fake_shared_tree(
        monkeypatch, {"sources": {"values": {"2000-01-01": ["earnings"]}}}
    )
    before = contract.shared_state()
    tree.sources.values_list[0].value.append("pensions")
    row = contract.module_parameters_unchanged(before)
    assert row["status"] == "fail" and "system:sources" in row["actual"]


def test_a_scale_metadata_or_band_change_is_caught(monkeypatch):
    band = {
        "threshold": {"values": {"2000-01-01": 0}},
        "amount": {"values": {"2000-01-01": 100}},
    }
    tree = _fake_shared_tree(
        monkeypatch,
        {"scale": {"metadata": {"type": "single_amount"}, "brackets": [band]}},
    )
    before = contract.shared_state()
    tree.scale.metadata["type"] = "marginal_amount"
    row = contract.module_parameters_unchanged(before)
    assert row["status"] == "fail" and "system:scale#node" in row["actual"]
    tree.scale.metadata["type"] = "single_amount"
    assert contract.module_parameters_unchanged(before)["status"] == "pass"
    tree.scale.brackets.append(tree.scale.brackets[0].clone())
    assert contract.module_parameters_unchanged(before)["status"] == "fail"


def test_reordered_bands_and_root_metadata_are_caught(monkeypatch):
    def band(rate):
        return {
            "threshold": {"values": {"2000-01-01": 0}},
            "rate": {"values": {"2000-01-01": rate}},
        }

    tree = _fake_shared_tree(
        monkeypatch, {"scale": {"brackets": [band(0.1), band(0.2)]}}
    )
    before = contract.shared_state()
    tree.scale.brackets.reverse()
    row = contract.module_parameters_unchanged(before)
    assert row["status"] == "fail" and "system:scale#node" in row["actual"]
    tree.scale.brackets.reverse()
    assert contract.module_parameters_unchanged(before)["status"] == "pass"
    tree.metadata["uprating"] = "wages"
    row = contract.module_parameters_unchanged(before)
    assert row["status"] == "fail" and "system:#node" in row["actual"]


def test_an_unusual_value_is_compared_without_stopping_the_run(monkeypatch):
    import datetime as dt

    tree = _fake_shared_tree(monkeypatch, {"p": {"values": {"2000-01-01": 1}}})
    tree.p.values_list[0].value = {dt.date(2020, 1, 1): 1}
    before = contract.shared_state()
    assert contract.module_parameters_unchanged(before)["status"] == "pass"
    tree.p.values_list[0].value[dt.date(2020, 1, 1)] = 2
    assert contract.module_parameters_unchanged(before)["status"] == "fail"


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


def test_the_capital_gains_cases_hold_on_every_in_process_route():
    pytest.importorskip("policyengine_uk.utils.dated_reforms")
    routes = contract.COUNTRY_ROUTES + contract.WRAPPER_ROUTES
    report = run_budget_reform_contract(
        routes=list(routes),
        cases=["mid_year_blended_rate", "cgt_retention_response"],
        max_examples=0,
    )
    failures = [row for row in report["cases"] if row["status"] in ("fail", "error")]
    assert failures == []
    # The response is checked, and passes, on every route.
    passed = {
        row["route"]
        for row in report["cases"]
        if row["case_id"] == "cgt_retention_response"
        and row["check"] == "change:capital_gains_tax:2027"
        and row["status"] == "pass"
    }
    assert passed == set(routes)


def test_the_default_response_is_reported_without_gating():
    """The default case's checks all wait on policyengine-uk#2396, so it
    reports the default response on every route without failing a run. The
    golden rows cover its rows on every route under fake routes; one real
    route checks that it runs and reports pending there."""
    pytest.importorskip("policyengine_uk.utils.dated_reforms")
    case = next(case for case in CASES if case.id == "cgt_default_response")
    assert {check.pending for check in case.checks} == {
        contract.DEFAULT_RESPONSE_DECISION
    }
    # No response settings: the case runs on whatever default is installed.
    assert not any(change.path.startswith("gov.simulation.") for change in case.changes)

    report = run_budget_reform_contract(
        routes=["country.reform_dict"],
        cases=["cgt_default_response"],
        max_examples=0,
    )
    rows = [row for row in report["cases"] if row["case_id"] == case.id]
    assert {row["status"] for row in rows} <= {"pass", "pending"}
    (response,) = (
        row for row in rows if row["check"] == "change:capital_gains_tax:2027"
    )
    assert response["status"] == "pending"
    assert response["decision_id"] == contract.DEFAULT_RESPONSE_DECISION


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
            # No cap reduction or deductions, so a payment equals its award.
            if variable in ("benefit_cap_reduction", "uc_deductions"):
                return [0.0]
            if (
                variable == "income_tax"
                and year == 2027
                and self.reform in (population.APRIL, population.FINITE)
            ):
                return [2.0]
            if self.reform == {"response": population.UC_STANDARD_ALLOWANCES}:
                # The award before deductions rises with the payment, so the
                # payment is the award less (unchanged) deductions.
                if variable in (
                    "uc_standard_allowance",
                    "universal_credit",
                    "universal_credit_pre_benefit_cap",
                ):
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
        "reason": "OSError",
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
    _assert_publishable_findings(rows)
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
    _assert_publishable_findings(rows)
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


# The Universal Credit allowance check's verdict, on synthetic benefit units.


def _uc_units(**columns):
    import numpy as np

    defaults = {
        "uc_standard_allowance": [400.0],
        "universal_credit": [500.0],
        "universal_credit_pre_benefit_cap": [500.0],
        "benefit_cap_reduction": [0.0],
        "uc_deductions": [0.0],
    }
    defaults.update(columns)
    return {name: np.array(values, dtype=float) for name, values in defaults.items()}


def _verdict(base, reformed):
    from policyengine.tax_benefit_models.uk.budget_reform_population import (
        uc_allowance_verdict,
    )

    return uc_allowance_verdict(base, reformed)


def _lawful_pair():
    """A capped unit whose deductions rise, and an uncapped unit that gains."""

    base = _uc_units(
        uc_standard_allowance=[400.0, 400.0],
        universal_credit_pre_benefit_cap=[900.0, 500.0],
        benefit_cap_reduction=[100.0, 0.0],
        uc_deductions=[20.0, 0.0],
        universal_credit=[780.0, 500.0],
    )
    reformed = _uc_units(
        uc_standard_allowance=[440.0, 440.0],
        universal_credit_pre_benefit_cap=[940.0, 540.0],
        benefit_cap_reduction=[140.0, 0.0],
        uc_deductions=[22.0, 0.0],
        universal_credit=[778.0, 540.0],
    )
    return base, reformed


def test_a_capped_award_whose_deductions_rise_with_the_allowance_holds():
    """SI 2013/376 reg 81 holds a capped award flat; deductions come out of it
    (SI 2013/380 Sch 6), so the amount paid falls by exactly their rise."""

    holds, detail = _verdict(*_lawful_pair())
    assert holds, detail
    assert detail["payments_lower"] == 1
    assert detail["awards_lower"] == 0


@pytest.mark.parametrize("rise", [2.0, 60.0, 357.0])
def test_how_much_deductions_rise_is_not_bounded(rise):
    """Deductions can start with a new award or exceed the allowance rise."""

    base, reformed = _lawful_pair()
    reformed["uc_deductions"][0] = 20.0 + rise
    reformed["universal_credit"][0] = 800.0 - 20.0 - rise
    holds, detail = _verdict(base, reformed)
    assert holds, detail


@pytest.mark.parametrize(
    ("change", "failing_key", "passing_value"),
    [
        (
            {"benefit_cap_reduction": 150.0, "universal_credit": 768.0},
            "awards_lower",
            0,
        ),
        (
            {"uc_deductions": 800.0, "universal_credit": 0.0},
            "payments_below_the_payable_floor",
            0,
        ),
        ({"uc_deductions": float("nan")}, "units_with_non_finite_values", 0),
        (
            {"benefit_cap_reduction": float("nan")},
            "units_with_non_finite_values",
            0,
        ),
        ({"universal_credit": 777.989}, "payments_not_award_less_deductions", 0),
        ({"universal_credit": 778.011}, "payments_not_award_less_deductions", 0),
        (
            {"uc_deductions": 0.0, "universal_credit": 780.0},
            "payments_not_award_less_deductions",
            0,
        ),
        (
            {"uc_standard_allowance": 430.0},
            "standard_allowance_scaled_10_percent",
            True,
        ),
    ],
    ids=[
        "award-falls-with-its-payment",
        "deductions-take-the-whole-award",
        "deductions-not-finite",
        "cap-reduction-not-finite",
        "payment-below-award-less-deductions",
        "payment-above-award-less-deductions",
        "deductions-released-but-payment-unchanged",
        "not-scaled",
    ],
)
def test_the_uc_allowance_check_fails_on_each_unlawful_movement(
    change, failing_key, passing_value
):
    base, reformed = _lawful_pair()
    assert _verdict(base, reformed)[0]
    for name, value in change.items():
        reformed[name][0] = value
    holds, detail = _verdict(base, reformed)
    assert not holds
    assert detail[failing_key] != passing_value, detail


@pytest.mark.parametrize(
    "change",
    [
        {"benefit_cap_reduction": 140.009},
        {"universal_credit": 777.991},
        {"universal_credit": 778.009},
    ],
    ids=["award-within-a-penny", "payment-a-little-low", "payment-a-little-high"],
)
def test_float32_rounding_within_a_penny_holds(change):
    base, reformed = _lawful_pair()
    for name, value in change.items():
        reformed[name][0] = value
    holds, detail = _verdict(base, reformed)
    assert holds, detail


def test_the_uc_allowance_check_fails_when_no_payment_rises():
    base = _uc_units()
    holds, detail = _verdict(base, _uc_units(uc_standard_allowance=[440.0]))
    assert not holds and detail["payments_higher"] == 0


def test_errors_that_cancel_across_units_still_fail():
    """The accounting identity holds per unit, not in aggregate."""

    base, reformed = _lawful_pair()
    reformed["universal_credit"][0] -= 5.0
    reformed["universal_credit"][1] += 5.0
    holds, detail = _verdict(base, reformed)
    assert not holds
    assert detail["payments_not_award_less_deductions"] == 2


@pytest.mark.parametrize(("gain", "holds"), [(0.009, False), (0.011, True)])
def test_a_gain_must_exceed_a_penny(gain, holds):
    """Only a payment more than a penny higher counts as responsive."""

    base = _uc_units(
        universal_credit_pre_benefit_cap=[900.0],
        benefit_cap_reduction=[100.0],
        universal_credit=[800.0],
    )
    reformed = _uc_units(
        uc_standard_allowance=[440.0],
        universal_credit_pre_benefit_cap=[940.0],
        benefit_cap_reduction=[140.0 - gain],
        universal_credit=[800.0 + gain],
    )
    assert _verdict(base, reformed)[0] is holds


@pytest.mark.parametrize(("relative", "holds"), [(5e-7, True), (2e-6, False)])
def test_the_allowance_must_scale_by_ten_percent(relative, holds):
    base, reformed = _lawful_pair()
    reformed["uc_standard_allowance"] = reformed["uc_standard_allowance"] * (
        1 + relative
    )
    assert _verdict(base, reformed)[0] is holds


def test_deductions_may_leave_exactly_the_payable_floor():
    """A penny an assessment period, 12p a year, is the lowest lawful payment."""

    base, reformed = _lawful_pair()
    reformed["uc_deductions"][0] = 800.0 - 0.12
    reformed["universal_credit"][0] = 0.12
    holds, detail = _verdict(base, reformed)
    assert holds, detail


@pytest.mark.parametrize("route", ["country.reform_dict", "wrapper.policy"])
def test_extraction_errors_and_unsupported_rows_carry_distinct_ids(monkeypatch, route):
    """#612 review: ids also label error, pending and unsupported rows."""

    from dataclasses import replace

    checks = (
        Check("variable", "income_tax", 2027, 0.0, "missing value"),
        Check("variable", "income_tax", 2027, 0.0, "missing pending", pending="d1344"),
        Check("baseline_equals", "income_tax", 2027, "income_tax", "baseline"),
    )
    fake(monkeypatch, FakeRoute(reformed={}, unreformed={}))
    rows = [
        row
        for row in evaluate_case(replace(CASE, checks=checks), route)
        if "assertion_id" in row
    ]
    assert len(rows) == len(checks)
    assert len({row["assertion_id"] for row in rows}) == len(checks)
    statuses = [row["status"] for row in rows]
    assert statuses[:2] == ["error", "pending"]
    if route == "wrapper.policy":
        assert statuses[2] == "unsupported"


@pytest.mark.parametrize("state", ["base", "reformed"])
@pytest.mark.parametrize(
    "name",
    [
        "uc_standard_allowance",
        "universal_credit",
        "universal_credit_pre_benefit_cap",
        "benefit_cap_reduction",
        "uc_deductions",
    ],
)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_any_non_finite_value_in_either_run_fails(state, name, value):
    """#614 round-3 review: finiteness is required of every input in both runs."""

    base, reformed = _lawful_pair()
    {"base": base, "reformed": reformed}[state][name][0] = value
    holds, detail = _verdict(base, reformed)
    assert not holds
    assert detail["units_with_non_finite_values"] == 1


@pytest.mark.parametrize("state", ["base", "reformed"])
@pytest.mark.parametrize(
    ("payment", "holds"), [(0.12, True), (0.115, True), (0.109, False)]
)
def test_the_payable_floor_holds_in_both_runs(state, payment, holds):
    """#614 round-3 review: a payment pushed below the floor fails in either run.

    The other run's payment sits exactly at the floor, and the deductions keep
    the accounting identity exact, so only this run's floor decides.
    """

    base, reformed = _lawful_pair()
    run = {"base": base, "reformed": reformed}[state]
    award = run["universal_credit_pre_benefit_cap"][0] - run["benefit_cap_reduction"][0]
    run["uc_deductions"][0] = award - payment
    run["universal_credit"][0] = payment
    other = reformed if state == "base" else base
    other_award = (
        other["universal_credit_pre_benefit_cap"][0] - other["benefit_cap_reduction"][0]
    )
    other["uc_deductions"][0] = other_award - 0.12
    other["universal_credit"][0] = 0.12
    result, detail = _verdict(base, reformed)
    assert result is holds, detail


def test_an_award_below_the_floor_is_paid_in_full():
    """#622 review: the floor is the lesser of the award and 12p a year."""

    import numpy as np

    base, reformed = _lawful_pair()
    for run in (base, reformed):
        unit = {
            "uc_standard_allowance": run["uc_standard_allowance"][0],
            "universal_credit_pre_benefit_cap": 0.05,
            "benefit_cap_reduction": 0.0,
            "uc_deductions": 0.0,
            "universal_credit": 0.05,
        }
        for name, value in unit.items():
            run[name] = np.append(run[name], value)
    holds, detail = _verdict(base, reformed)
    assert holds, detail


# Reform identities on rows (receipt schema v1).


def test_each_route_binds_the_reform_it_consumes():
    from policyengine_uk.utils.scenario import Scenario

    from policyengine.provenance.receipt import (
        reform_identity,
        scenario_reform_identity,
    )

    case = next(case for case in CASES if case.id == "april_rate_change")
    expected = {
        "country.reform_dict": reform_identity(
            contract.represent(case, "country.reform_dict"),
            "policyengine-uk.reform_dict/v1",
            name=case.id,
        ),
        "country.scenario_parameter_changes": scenario_reform_identity(
            Scenario(
                parameter_changes=contract.represent(
                    case, "country.scenario_parameter_changes"
                )
            ),
            name=case.id,
        ),
        "wrapper.household": reform_identity(
            contract.represent(case, "wrapper.household"),
            "policyengine.reform_dict/v1",
            name=case.id,
        ),
        "wrapper.policy": reform_identity(
            contract.represent(case, "wrapper.policy"),
            "policyengine.reform_dict/v1",
            name=case.id,
        ),
    }
    for route, identity in expected.items():
        bound, unavailable = contract.row_reform_identity(
            case, route, contract.represent(case, route)
        )
        assert bound == identity.model_dump(mode="json"), route
        assert unavailable is None
        assert bound["name"] == case.id and bound["kind"] == "reform"
    # The two dict representations of one change differ, and are not merged.
    assert (
        expected["country.reform_dict"].reform_sha256
        != expected["wrapper.household"].reform_sha256
    )


@pytest.mark.parametrize(
    "case_id, route, reason",
    [
        ("april_rate_change", "country.reform_from_dict", "no representation"),
        ("april_rate_change", "api.sim_api", "in-process"),
        ("modifier_then_parameter_changes", "country.reform_dict", "closure"),
        ("parameter_changes_then_modifier", "wrapper.policy", "closure"),
    ],
)
def test_an_unbindable_reform_has_no_identity_and_says_why(case_id, route, reason):
    case = next(case for case in CASES if case.id == case_id)
    representation = (
        None
        if route in contract.UNSUPPORTED_ROUTES
        else contract.represent(case, route)
    )
    bound, unavailable = contract.row_reform_identity(case, route, representation)
    assert bound is None and reason in unavailable


def test_a_value_receipts_refuse_gives_no_identity_rather_than_an_error(
    monkeypatch,
):
    import policyengine.provenance.receipt as receipt

    def refuse(*args, **kwargs):
        raise receipt.ReceiptError("$.payload.p.2027: inf is not a finite number.")

    monkeypatch.setattr(receipt, "reform_identity", refuse)
    case = next(case for case in CASES if case.id == "april_rate_change")
    bound, unavailable = contract.row_reform_identity(
        case, "country.reform_dict", contract.represent(case, "country.reform_dict")
    )
    assert bound is None and unavailable.startswith("ReceiptError")


def test_rows_carry_their_reform_identity(monkeypatch):
    fake(
        monkeypatch,
        FakeRoute(
            reformed={
                ("parameter", RATE, 2027): 0.21,
                ("variable", "income_tax", 2027): 3_660.30,
            },
            unreformed={("variable", "income_tax", 2027): 3_486.00},
        ),
    )
    rows = evaluate_case(CASE, "country.reform_dict")
    identities = {json.dumps(row["reform_identity"], sort_keys=True) for row in rows}
    assert len(identities) == 1
    (identity,) = [row["reform_identity"] for row in rows[:1]]
    assert identity["representation"] == "policyengine-uk.reform_dict/v1"
    assert identity["name"] == CASE.id
    assert all("reform_identity_unavailable" not in row for row in rows)
    (unsupported,) = evaluate_case(CASE, "api.sim_api")
    assert unsupported["reform_identity"] is None
    assert unsupported["reform_identity_unavailable"]


def test_run_level_rows_say_they_run_no_reform():
    row = contract.module_parameters_unchanged(contract.shared_state())
    assert row["reform_identity"] is None
    assert row["reform_identity_unavailable"] == "a run-level row runs no reform"


def test_a_scenario_that_cannot_hold_a_change_gives_no_identity(monkeypatch):
    import policyengine_uk.utils.scenario as scenario_module

    class Refusing:
        def __init__(self, **kwargs):
            raise ValueError("parameter_changes: not a number")

    monkeypatch.setattr(scenario_module, "Scenario", Refusing)
    case = next(case for case in CASES if case.id == "april_rate_change")
    route = "country.scenario_parameter_changes"
    bound, unavailable = contract.row_reform_identity(
        case, route, contract.represent(case, route)
    )
    assert bound is None and unavailable.startswith("ValueError")


def test_every_report_row_has_a_reform_identity_field():
    report = run_budget_reform_contract(routes=["api.sim_api"], max_examples=1)
    for section in ("cases", "properties", "population"):
        for row in report[section]:
            assert "reform_identity" in row, (section, row)
            if row["reform_identity"] is None:
                assert row["reform_identity_unavailable"], (section, row)


# The small-cell rule and flat findings in population rows.


def _is_condition(key, value):
    """A finding the check requires; ``*_informational`` ones it does not."""
    return isinstance(value, bool) and not key.endswith("_informational")


def _small_counts(value, path="detail"):
    """Where ``value`` holds a count from 1 to 9."""
    import numbers

    import numpy as np

    if isinstance(value, (bool, np.bool_)):
        return []
    if isinstance(value, numbers.Integral):
        return [path] if 0 < value < 10 else []
    if isinstance(value, dict):
        return [
            found
            for key, item in value.items()
            for found in _small_counts(item, f"{path}.{key}")
        ]
    if isinstance(value, (list, tuple)):
        return [
            found
            for index, item in enumerate(value)
            for found in _small_counts(item, f"{path}[{index}]")
        ]
    return []


def _assert_publishable_findings(rows):
    """No small count anywhere, and a row passes when all its findings hold."""
    for row in rows:
        assert _small_counts(row) == [], row
        detail = row.get("detail")
        if row["route"] == "-":
            continue
        assert isinstance(detail, dict), row
        findings = {
            key: value for key, value in detail.items() if _is_condition(key, value)
        }
        assert findings, row
        assert (row["status"] == "pass") == all(findings.values()), row


def test_publishable_detail_suppresses_counts_from_1_to_9_at_any_depth():
    import numpy as np

    from policyengine.tax_benefit_models.uk.budget_reform_population import (
        FEWER_THAN_10,
        publishable_detail,
    )

    detail = {
        "none": 0,
        "one": 1,
        "nine": 9,
        "ten": 10,
        "negative": -3,
        "finding": True,
        "other_finding": False,
        "total": 3.5,
        "numpy_count": np.int64(5),
        "nested": {"count": 4, "list": [2, 12, {"deep": 7}]},
    }
    assert publishable_detail(detail) == {
        "none": 0,
        "one": FEWER_THAN_10,
        "nine": FEWER_THAN_10,
        "ten": 10,
        "negative": -3,
        "finding": True,
        "other_finding": False,
        "total": 3.5,
        "numpy_count": FEWER_THAN_10,
        "nested": {
            "count": FEWER_THAN_10,
            "list": [FEWER_THAN_10, 12, {"deep": FEWER_THAN_10}],
        },
    }


def _equal_but_small_counts(original, published):
    """``published`` is ``original`` with only its small counts suppressed."""
    import numbers

    from policyengine.tax_benefit_models.uk.budget_reform_population import (
        FEWER_THAN_10,
    )

    if isinstance(original, bool):
        return published is original
    if isinstance(original, numbers.Integral) and 0 < original < 10:
        return published == FEWER_THAN_10
    if isinstance(original, dict):
        return published.keys() == original.keys() and all(
            _equal_but_small_counts(value, published[key])
            for key, value in original.items()
        )
    if isinstance(original, (list, tuple)):
        return len(published) == len(original) and all(
            _equal_but_small_counts(a, b) for a, b in zip(original, published)
        )
    return published == original


def test_publication_removes_every_small_count_and_nothing_else():
    pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    from policyengine.tax_benefit_models.uk.budget_reform_population import (
        publishable_detail,
    )

    leaves = st.one_of(
        st.booleans(),
        st.integers(-20, 1_000),
        st.floats(allow_nan=False),
        st.text(max_size=5),
        st.none(),
    )
    details = st.recursive(
        leaves,
        lambda children: st.one_of(
            st.lists(children, max_size=4),
            st.dictionaries(st.text(max_size=5), children, max_size=4),
        ),
        max_leaves=20,
    )

    @settings(max_examples=200, deadline=None, derandomize=True)
    @given(details)
    def check(detail):
        published = publishable_detail(detail)
        assert _small_counts(published) == []
        assert _equal_but_small_counts(detail, published)
        assert publishable_detail(published) == published

    check()


def test_a_total_over_fewer_than_10_changed_records_is_withheld():
    from policyengine.tax_benefit_models.uk.budget_reform_population import (
        WITHHELD_FEWER_THAN_10,
        total_over_records,
    )

    assert total_over_records(12.5, 0) == 12.5
    assert total_over_records(12.5, 1) == WITHHELD_FEWER_THAN_10
    assert total_over_records(12.5, 9) == WITHHELD_FEWER_THAN_10
    assert total_over_records(12.5, 10) == 12.5
    # Any small count of the records behind it withholds it.
    assert total_over_records(300.0, 10, 3) == WITHHELD_FEWER_THAN_10
    assert total_over_records(300.0, 10, 0) == 300.0


def test_uc_findings_agree_with_their_counts_and_the_verdict():
    pytest.importorskip("hypothesis")
    import numpy as np
    from hypothesis import given, settings
    from hypothesis import strategies as st

    from policyengine.tax_benefit_models.uk.budget_reform_population import (
        UC_ALLOWANCE_VARIABLES,
    )

    amounts = st.one_of(st.floats(0, 2_000), st.just(float("nan")))
    verdicts = set()

    # From the lawful pair (one capped unit whose payment falls with its
    # deductions, one that gains), so verdicts that hold are drawn too; each
    # example changes up to three of its values.
    @settings(max_examples=200, deadline=None, derandomize=True)
    @given(data=st.data())
    def check(data):
        base, reformed = _lawful_pair()
        for _ in range(data.draw(st.integers(0, 3))):
            state = data.draw(st.sampled_from([base, reformed]))
            name = data.draw(st.sampled_from(UC_ALLOWANCE_VARIABLES))
            unit = data.draw(st.integers(0, 1))
            state[name] = np.array(state[name], dtype=float)
            state[name][unit] = data.draw(amounts)
        holds, detail = _verdict(base, reformed)
        verdicts.add(holds)
        counts = {
            "no_award_lower": "awards_lower",
            "payments_are_award_less_deductions": "payments_not_award_less_deductions",
            "no_payment_below_the_payable_floor": "payments_below_the_payable_floor",
            "no_non_finite_units": "units_with_non_finite_values",
            "no_payment_lower_informational": "payments_lower",
        }
        for finding, count in counts.items():
            assert detail[finding] is (detail[count] == 0), finding
        assert detail["some_payment_higher"] is (detail["payments_higher"] > 0)
        # The verdict as it was defined from the counts.
        assert holds == (
            detail["units_with_non_finite_values"] == 0
            and detail["standard_allowance_scaled_10_percent"]
            and detail["awards_lower"] == 0
            and detail["payments_not_award_less_deductions"] == 0
            and detail["payments_below_the_payable_floor"] == 0
            and detail["payments_higher"] > 0
        )

    check()
    assert verdicts == {True, False}


def test_population_rows_state_each_condition_as_a_flat_finding(stub_population_checks):
    population = stub_population_checks
    rows = population.run_population_checks("unused.h5", list(contract.COUNTRY_ROUTES))
    _assert_publishable_findings(rows)
    outputs = {
        f"{variable}:{year}_matches"
        for variable in population.OUTPUTS
        for year in population.YEARS
    }
    expected = {
        population.POPULATION_BASELINE_ISOLATION: outputs,
        population.POPULATION_QUERY_ORDER: outputs,
        population.POPULATION_ROUTES_AGREE: {
            "income_tax:2026_matches",
            "income_tax:2027_matches",
        },
        population.POPULATION_APRIL_RATE_CHANGE: {"2026_unchanged", "2027_total_rises"},
        population.POPULATION_FINITE_CHANGE_EXPIRES: {"income_tax:2028_matches"},
        population.POPULATION_UC_STANDARD_ALLOWANCE_PLUS_10: {
            "standard_allowance_scaled_10_percent",
            "no_award_lower",
            "payments_are_award_less_deductions",
            "no_payment_below_the_payable_floor",
            "some_payment_higher",
            "no_non_finite_units",
            "no_payment_lower_informational",
        },
        population.POPULATION_STATE_PENSION_PLUS_10: {
            "basic_and_new_scaled_10_percent",
            "no_pension_lower",
            "some_pension_higher",
        },
    }
    for row in rows:
        findings = {
            key for key, value in row["detail"].items() if isinstance(value, bool)
        }
        assert findings == expected[row["check_id"]], row
    # The stub moves one person's tax: one record, so the count reads
    # "fewer than 10" and the total is withheld.
    april = next(
        row
        for row in rows
        if row["check_id"] == population.POPULATION_APRIL_RATE_CHANGE
    )
    assert april["detail"]["2027_people_with_higher_tax"] == population.FEWER_THAN_10
    assert april["detail"]["2027_total_change"] == population.WITHHELD_FEWER_THAN_10


def test_a_detail_of_another_type_is_an_error_not_passed_through():
    import numpy as np

    from policyengine.tax_benefit_models.uk.budget_reform_population import (
        publishable_detail,
    )

    assert publishable_detail({"finding": np.bool_(True)}) == {"finding": True}
    assert type(publishable_detail(np.bool_(False))) is bool
    for unchecked in (np.array([3, 12]), {3, 12}, {3: "count key"}):
        with pytest.raises(TypeError):
            publishable_detail({"value": unchecked})


def _run_population_with(monkeypatch, array, routes=None):
    """Run the population checks on arrays from ``array(tag, variable, year)``.

    ``tag`` is None for an unreformed simulation, and otherwise names the
    route and reform: the reform dict's repr, or a repr containing
    "scenario" or "from_dict", or one starting "('baseline'" for a reformed
    simulation's baseline.
    """
    from types import SimpleNamespace

    import policyengine_uk
    from policyengine_core.reforms import Reform
    from policyengine_uk.utils import scenario

    from policyengine.tax_benefit_models.uk import (
        budget_reform_population as population,
    )

    class Simulation:
        def __init__(self, dataset, reform=None, scenario=None):
            self.tag = (
                None
                if reform is None and scenario is None
                else repr(reform if scenario is None else ("scenario", scenario))
            )

        @property
        def baseline(self):
            baseline = Simulation(dataset=None)
            if self.tag is not None:
                baseline.tag = repr(("baseline", self.tag))
            return baseline

        def calculate(self, variable, year):
            return array(self.tag, variable, year)

    with monkeypatch.context() as patch:
        patch.setattr(policyengine_uk, "Microsimulation", Simulation)
        patch.setattr(
            scenario, "Scenario", lambda **kwargs: repr(sorted(kwargs.items()))
        )
        patch.setattr(
            Reform,
            "from_dict",
            staticmethod(lambda reform, **kwargs: ("from_dict", repr(reform))),
        )
        patch.setattr(
            population, "subsample", lambda *args: SimpleNamespace(copy=lambda: None)
        )
        patch.setattr(population, "plus_ten_percent", lambda paths: {"response": paths})
        return population.run_population_checks(
            "unused.h5", routes or list(contract.COUNTRY_ROUTES)
        )


def test_every_population_row_publishes_the_findings_that_decide_it(monkeypatch):
    """On random arrays: no small count, and each row passes when its findings do."""
    pytest.importorskip("hypothesis")
    pytest.importorskip("policyengine_uk.utils.scenario")
    import numpy as np
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st

    from policyengine.tax_benefit_models.uk import (
        budget_reform_population as population,
    )

    passes = set()

    @settings(
        max_examples=60,
        deadline=None,
        derandomize=True,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(data=st.data())
    def check(data):
        units = data.draw(st.integers(1, 12))
        amounts = st.floats(0, 1_000, width=32)
        if data.draw(st.booleans()):
            amounts = st.one_of(amounts, st.just(float("nan")))
        # Lawful responses: the Universal Credit and State Pension
        # simulations move their awards as the law does, so those rows can
        # pass; otherwise every reformed array is random or unreformed.
        lawful = data.draw(st.booleans())
        pensions = ("basic_state_pension", "new_state_pension", "state_pension")
        arrays = {}

        def drawn(variable):
            values = amounts
            if lawful and variable == "uc_standard_allowance":
                values = st.floats(1, 1_000, width=32)
            return np.array(
                data.draw(st.lists(values, min_size=units, max_size=units)),
                dtype=float,
            )

        def array(tag, variable, year):
            key = (tag, variable, year)
            if key in arrays:
                return arrays[key]
            if tag is None:
                if lawful and variable in ("benefit_cap_reduction", "uc_deductions"):
                    value = np.zeros(units)
                elif lawful and variable == "universal_credit_pre_benefit_cap":
                    value = array(None, "universal_credit", year)
                else:
                    value = drawn(variable)
            elif (
                lawful
                and "universal_credit.standard_allowance" in tag
                and variable in population.UC_ALLOWANCE_VARIABLES
            ):
                allowance = array(None, "uc_standard_allowance", year)
                base = array(None, variable, year)
                value = {
                    "uc_standard_allowance": 1.1 * allowance,
                    "universal_credit_pre_benefit_cap": base + 0.1 * allowance,
                    "universal_credit": base + 0.1 * allowance,
                }.get(variable, base)
            elif lawful and "state_pension" in tag and variable in pensions:
                value = 1.1 * array(None, variable, year)
            elif data.draw(st.booleans()):
                value = array(None, variable, year)
            else:
                value = drawn(variable)
            arrays[key] = value
            return value

        rows = _run_population_with(monkeypatch, array)
        _assert_publishable_findings(rows)
        passes.update((row["check_id"], row["status"]) for row in rows)

    check()
    # Every country check both passed and failed somewhere in the run.
    for check_id in population.COUNTRY_POPULATION_CHECKS:
        assert {(check_id, "pass"), (check_id, "fail")} <= passes, check_id


def _steady(tag, variable, year):
    """Arrays where every reform moves nothing: one unit at 1."""
    import numpy as np

    return np.ones(1)


def test_routes_that_differ_only_in_2026_disagree(monkeypatch):
    pytest.importorskip("policyengine_uk.utils.scenario")
    import numpy as np

    from policyengine.tax_benefit_models.uk import (
        budget_reform_population as population,
    )

    def array(tag, variable, year):
        if variable == "income_tax" and tag is not None and "baseline" not in tag:
            if year == 2026 and "scenario" in tag:
                return np.array([5.0])
            if year == 2027:
                return np.array([2.0])
        return _steady(tag, variable, year)

    rows = _run_population_with(monkeypatch, array)
    _assert_publishable_findings(rows)
    agree = {
        row["route"]: row
        for row in rows
        if row["check_id"] == population.POPULATION_ROUTES_AGREE
    }
    scenario_row = agree["country.reform_dict = country.scenario_parameter_changes"]
    assert scenario_row["status"] == "fail"
    assert scenario_row["detail"] == {
        "income_tax:2026_matches": False,
        "income_tax:2027_matches": True,
    }
    assert agree["country.reform_dict = country.reform_from_dict"]["status"] == "pass"


def test_a_state_pension_that_falls_fails_the_pension_check(monkeypatch):
    pytest.importorskip("policyengine_uk.utils.scenario")
    import numpy as np

    from policyengine.tax_benefit_models.uk import (
        budget_reform_population as population,
    )

    def array(tag, variable, year):
        if tag is not None and "state_pension" in tag:
            if variable in ("basic_state_pension", "new_state_pension"):
                return np.array([1.1, 1.1])
            if variable == "state_pension":
                # One higher, one lower: the rates scaled, yet a pension fell.
                return np.array([1.1, 0.9])
        return np.ones(2)

    rows = _run_population_with(monkeypatch, array, ["country.reform_dict"])
    _assert_publishable_findings(rows)
    pension = next(
        row
        for row in rows
        if row["check_id"] == population.POPULATION_STATE_PENSION_PLUS_10
    )
    assert pension["status"] == "fail"
    assert pension["detail"]["basic_and_new_scaled_10_percent"] is True
    assert pension["detail"]["some_pension_higher"] is True
    assert pension["detail"]["no_pension_lower"] is False


def test_a_few_large_changes_among_tiny_ones_withhold_the_total(monkeypatch):
    """Three people's £100 rises with seven negligible changes: three records."""
    pytest.importorskip("policyengine_uk.utils.scenario")
    import numpy as np

    from policyengine.tax_benefit_models.uk import (
        budget_reform_population as population,
    )

    def array(tag, variable, year):
        tax = np.ones(10)
        if (
            variable == "income_tax"
            and year == 2027
            and tag is not None
            and "baseline" not in tag
        ):
            return tax + np.array([100.0] * 3 + [4.77e-7] * 7)
        return tax

    rows = _run_population_with(monkeypatch, array, ["country.reform_dict"])
    april = next(
        row
        for row in rows
        if row["check_id"] == population.POPULATION_APRIL_RATE_CHANGE
    )
    assert april["detail"]["2027_people_with_higher_tax"] == population.FEWER_THAN_10
    assert april["detail"]["2027_total_change"] == population.WITHHELD_FEWER_THAN_10


def test_a_detail_that_cannot_be_checked_turns_its_row_into_an_error(monkeypatch):
    pytest.importorskip("policyengine_uk.utils.scenario")
    import numpy as np

    from policyengine.tax_benefit_models.uk import (
        budget_reform_population as population,
    )

    monkeypatch.setattr(
        population,
        "uc_allowance_verdict",
        lambda base, reformed: (True, {"counts": np.array([3, 12])}),
    )
    rows = _run_population_with(monkeypatch, _steady, ["country.reform_dict"])
    uc = next(
        row
        for row in rows
        if row["check_id"] == population.POPULATION_UC_STANDARD_ALLOWANCE_PLUS_10
    )
    assert uc["status"] == "error"
    assert uc["reason"] == "TypeError"
    assert uc["detail"] is None
    assert all(row["status"] != "error" for row in rows if row is not uc)


def test_a_total_moved_only_by_tiny_changes_in_few_records_is_withheld(
    monkeypatch, stub_population_checks
):
    """Withheld by the records that moved at all, not just past the threshold."""
    import numpy as np
    import policyengine_uk

    population = stub_population_checks
    stub = policyengine_uk.Microsimulation
    calculate = stub.calculate

    def three_people(self, variable, year):
        if variable != "income_tax":
            return calculate(self, variable, year)
        tax = np.full(3, 1.0)
        if year == 2027 and self.reform in (population.APRIL, population.FINITE):
            # Each below the 1e-6 threshold the counts use; together above it.
            return tax + 4.77e-7
        return tax

    monkeypatch.setattr(stub, "calculate", three_people)
    rows = population.run_population_checks("unused.h5", ["country.reform_dict"])
    april = next(
        row
        for row in rows
        if row["check_id"] == population.POPULATION_APRIL_RATE_CHANGE
    )
    assert april["detail"]["2027_people_with_higher_tax"] == 0
    assert april["detail"]["2027_total_rises"] is True
    assert april["detail"]["2027_total_change"] == population.WITHHELD_FEWER_THAN_10
