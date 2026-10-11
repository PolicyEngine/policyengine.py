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
    def __init__(self, reformed, unreformed, isolation=(), error=None):
        self.reformed, self.unreformed = reformed, unreformed
        self.isolation, self.error = list(isolation), error

    def run(self, case, representation, cache):
        if self.error is not None:
            raise self.error
        run = RouteRun()
        run.reformed.update(self.reformed)
        run.unreformed.update(self.unreformed)
        run.isolation.extend(self.isolation)
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
    assert {row["status"] for row in report["cases"]} == {"unsupported"}
    assert all(row["reason"] for row in report["cases"])
    assert report["summary"]["fail"] == 0 and report["summary"]["error"] == 0
    assert report["holds"] is True
    with pytest.raises(ValueError, match="Unknown routes"):
        run_budget_reform_contract(routes=["country.typo"])


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
