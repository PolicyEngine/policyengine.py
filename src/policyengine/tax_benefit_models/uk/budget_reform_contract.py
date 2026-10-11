"""The UK Budget reform contract.

A Budget dates its measures: a rate from 6 April, a freeze extended to a
later tax year, a change that ends, an April uprating schedule, a rate that
changes part-way through a year. This contract checks that each such reform
gives the right answer through every supported route, against expected
values derived independently of the model (statute arithmetic, or a
day-weighted fiscal-year annualisation written here), and that applying a
reform never changes the baseline.

Qualification imports :func:`run_budget_reform_contract` and gates a
candidate model and data pair on its report. The contract lives here rather
than in policyengine-uk so a candidate model release never grades itself.

Routes
------

``country.reform_dict``
    ``policyengine_uk.Simulation(reform=dict)`` with ``"start.stop"`` keys.
``country.scenario_parameter_changes``
    ``policyengine_uk.Simulation(scenario=Scenario(parameter_changes=dict))``.
``country.reform_from_dict``
    ``policyengine_uk.Simulation(reform=Reform.from_dict(dict))``.
``wrapper.household``
    ``policyengine.uk.calculate_household(reform=dict)``, with a lone date
    for a change in force from that date and ``"start.stop"`` for a bounded
    one.
``wrapper.policy``
    ``policyengine.core.Simulation(policy=Policy(...))`` over an in-memory
    dataset holding the case's household (and, with ``dataset_path``, over a
    deterministic subsample of the certified dataset).
``api.sim_api``
    Not run in-process: policyengine-sim-api's deploy gate imports
    :data:`CASES` and routes them through its runtime.

Readings
--------

Every case is written once as :class:`Change` objects on the statutory
timeline: a value in force from ``start`` to ``stop`` inclusive, or from
``start`` on (held flat) when ``stop`` is None. Each route receives the
representation it documents. Documented differences between readings (a
bare-year policyengine-uk dict key is that fiscal year only, while
``Reform.from_dict`` reads it as onwards) are covered by the country-only
reading cases.

Prior law after a bounded change
--------------------------------

Contract 1.0.0 expects prior law's projected path to resume after a bounded
change (``PRIOR_LAW_OPTION = "projected"``). Whether indexation should
instead resume from a changed statutory amount (Income Tax Act 2007 s57
indexes "the amount ... for the previous tax year") is an open methodology
call (cos d1344). Checks that depend on it carry ``pending`` and never gate.

Report
------

A JSON-serialisable dict: ``contract_id``, ``contract_version``,
``prior_law_option``, installed ``versions``, the dataset's sha256 when one
is given, ``cases`` (one row per case, route and check, with ``status`` of
``pass``, ``fail``, ``error``, ``unsupported`` or ``pending``),
``properties`` and ``summary`` counts. Any ``fail`` or ``error`` means the
contract does not hold.
"""

from __future__ import annotations

import datetime
import gc
import hashlib
import importlib.metadata
import json
import math
import random
import re
import sys
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, Decimal
from typing import Any, Optional, Union

CONTRACT_ID = "policyengine-uk/budget-reform-contract"
CONTRACT_VERSION = "1.0.0"
PRIOR_LAW_OPTION = "projected"
PRIOR_LAW_DECISION = "d1344"
FLAT_STOP = datetime.date(2100, 12, 31)

COUNTRY_ROUTES = (
    "country.reform_dict",
    "country.scenario_parameter_changes",
    "country.reform_from_dict",
)
WRAPPER_ROUTES = ("wrapper.household", "wrapper.policy")
API_ROUTE = "api.sim_api"
ROUTES = COUNTRY_ROUTES + WRAPPER_ROUTES + (API_ROUTE,)
UNSUPPORTED_ROUTES = {
    API_ROUTE: (
        "Runs in policyengine-sim-api's deploy gate, which imports CASES and "
        "routes them through its runtime; it is not callable in-process."
    ),
}

PASS, FAIL, ERROR, UNSUPPORTED, PENDING = (
    "pass",
    "fail",
    "error",
    "unsupported",
    "pending",
)

BASIC_RATE = "gov.hmrc.income_tax.rates.uk[0].rate"
PERSONAL_ALLOWANCE = "gov.hmrc.income_tax.allowances.personal_allowance.amount"
BASIC_RATE_LIMIT = "gov.hmrc.income_tax.rates.uk[1].threshold"
UC_SINGLE_OLD = "gov.dwp.universal_credit.standard_allowance.amount.SINGLE_OLD"
NEW_STATE_PENSION = "gov.dwp.state_pension.new_state_pension.amount"
CGT_BASIC_RATE = "gov.hmrc.cgt.basic_rate"
VAT_STANDARD_RATE = "gov.hmrc.vat.standard_rate"
PROTECTED_LCWRA = "gov.dwp.universal_credit.rebalancing.protected_health_element"
CPI_SEPTEMBER = "gov.economic_assumptions.statutory_uprating_inputs.cpi_september"
MA_INCOME_CONDITION = (
    "gov.contrib.cps.marriage_tax_reforms.expanded_ma.remove_income_condition"
)
SEPTEMBER_CPI_RISE = "gov.economic_assumptions.yoy_growth.september_cpi_uprating"
NICS = "gov.hmrc.national_insurance"
PRIMARY_THRESHOLD = f"{NICS}.class_1.thresholds.primary_threshold"
UPPER_EARNINGS_LIMIT = f"{NICS}.class_1.thresholds.upper_earnings_limit"
LOWER_PROFITS_LIMIT = f"{NICS}.class_4.thresholds.lower_profits_limit"
UPPER_PROFITS_LIMIT = f"{NICS}.class_4.thresholds.upper_profits_limit"


# Case definitions.


@dataclass(frozen=True)
class Change:
    """A value in force on the statutory timeline.

    From ``start`` to ``stop`` inclusive, or from ``start`` on, held flat,
    when ``stop`` is None.
    """

    path: str
    start: datetime.date
    value: Any
    stop: Optional[datetime.date] = None

    @property
    def interval_key(self) -> str:
        return f"{self.start}.{self.stop or FLAT_STOP}"


@dataclass(frozen=True)
class Household:
    """One benefit unit in one household; values hold in every year."""

    people: tuple[Mapping[str, Any], ...]
    benunit: Mapping[str, Any] = field(default_factory=dict)
    household: Mapping[str, Any] = field(default_factory=dict)


Expected = Union[float, Callable[["Context"], float]]


@dataclass(frozen=True)
class Check:
    """An expected value.

    ``target``:
    - ``"parameter"``: the annual value of parameter ``name`` in fiscal year
      ``year`` (read at 1 January of ``year``, as annual formulas read it);
    - ``"variable"``: the household's total of variable ``name`` in ``year``;
    - ``"change"``: that total under the reform minus without it, through
      the same route.

    ``expected`` is a number or a function of the :class:`Context`. ``oracle``
    says how it was derived. ``pending`` names an open decision: the check is
    reported but does not gate.
    """

    target: str
    name: str
    year: int
    expected: Expected
    oracle: str
    tolerance: float = 1e-6
    pending: Optional[str] = None


@dataclass(frozen=True)
class Case:
    """A dated reform and what it must produce.

    ``representations`` overrides the representation a route receives, for
    the reading cases; ``routes`` limits the routes a case runs on.
    ``expect_error`` is a regular expression the error must match for a
    reform every route must reject.
    """

    id: str
    title: str
    changes: tuple[Change, ...]
    household: Household
    checks: tuple[Check, ...] = ()
    expect_error: Optional[str] = None
    routes: Optional[tuple[str, ...]] = None
    representations: Mapping[str, Any] = field(default_factory=dict)


class Context:
    """What an expected value may read: current law's annual parameters."""

    def __init__(self, baseline_parameter: Callable[[str, int], float]):
        self._baseline_parameter = baseline_parameter

    def baseline(self, path: str, year: int) -> float:
        return self._baseline_parameter(path, year)


def _date(text: str) -> datetime.date:
    return datetime.date.fromisoformat(text)


def adult(income: float = 30_000, **extra) -> Household:
    return Household(people=({"age": 40, "employment_income": income, **extra},))


def s57_personal_allowance(previous: float, increase: float) -> float:
    """Income Tax Act 2007 s57(3): add the rise, rounded up to £10."""
    if increase <= 0:
        return previous
    rise = Decimal(repr(float(previous))) * Decimal(repr(float(increase)))
    return float(
        Decimal(repr(float(previous)))
        + (rise / 10).to_integral_value(ROUND_CEILING) * 10
    )


def s21_basic_rate_limit(previous: float, increase: float) -> float:
    """Income Tax Act 2007 s21(3): scale, rounded up to £100."""
    if increase <= 0:
        return previous
    scaled = Decimal(repr(float(previous))) * (1 + Decimal(repr(float(increase))))
    return float((scaled / 100).to_integral_value(ROUND_CEILING) * 100)


def weekly(annual: float) -> float:
    """The weekly NICs convention: the annual amount over 52, to the penny."""
    return float((Decimal(repr(float(annual))) / 52).quantize(Decimal("0.01")))


def fiscal_year_average(
    pieces: Sequence[tuple[datetime.date, float]], year: int
) -> float:
    """Day-weighted average over 6 April to 5 April of a step function.

    ``pieces`` lists (date the value takes effect, value), in any order.
    """
    start = datetime.date(year, 4, 6)
    end = datetime.date(year + 1, 4, 6)
    ordered = sorted(pieces)
    total = 0.0
    day = start
    while day < end:
        value = None
        for effective, piece_value in ordered:
            if effective <= day:
                value = piece_value
        total += value
        day += datetime.timedelta(days=1)
    return total / (end - start).days


def _uplift(
    year: int, rate: float, income: float = 30_000
) -> Callable[[Context], float]:
    def expected(context: Context) -> float:
        allowance = context.baseline(PERSONAL_ALLOWANCE, year)
        return (income - allowance) * (rate - context.baseline(BASIC_RATE, year))

    return expected


def _freeze_change(year: int) -> Callable[[Context], float]:
    def expected(context: Context) -> float:
        frozen_out = context.baseline(PERSONAL_ALLOWANCE, year) - 12_570
        return context.baseline(BASIC_RATE, year) * frozen_out

    return expected


def _statutory_resumption(path: str) -> Callable[[Context], float]:
    def expected(context: Context) -> float:
        increase = context.baseline(SEPTEMBER_CPI_RISE, 2034)
        if path == PERSONAL_ALLOWANCE:
            return s57_personal_allowance(12_570, increase)
        return s21_basic_rate_limit(37_700, increase)

    return expected


def _baseline_value(path: str, year: int) -> Callable[[Context], float]:
    return lambda context: context.baseline(path, year)


INCOME_UPLIFT_ORACLE = (
    "(30,000 - personal allowance) x (new rate - current rate); the allowance "
    "and current rate are read from current law"
)

CASES: tuple[Case, ...] = (
    Case(
        id="april_rate_change",
        title="Basic rate 21% from 6 April 2027",
        changes=(Change(BASIC_RATE, _date("2027-04-06"), 0.21),),
        household=adult(),
        checks=(
            Check("parameter", BASIC_RATE, 2026, 0.20, "unchanged before 2027-28"),
            Check("parameter", BASIC_RATE, 2027, 0.21, "in force on 30 April 2027"),
            Check("parameter", BASIC_RATE, 2028, 0.21, "held from 6 April 2027"),
            Check("change", "income_tax", 2026, 0.0, "before the change", 0.005),
            Check(
                "change",
                "income_tax",
                2027,
                _uplift(2027, 0.21),
                INCOME_UPLIFT_ORACLE,
                0.005,
            ),
            Check(
                "change",
                "income_tax",
                2028,
                _uplift(2028, 0.21),
                INCOME_UPLIFT_ORACLE,
                0.005,
            ),
        ),
    ),
    Case(
        id="finite_rate_change",
        title="Basic rate 21% for 2027-28 only",
        changes=(Change(BASIC_RATE, _date("2027-04-06"), 0.21, _date("2028-04-05")),),
        household=adult(),
        checks=(
            Check("parameter", BASIC_RATE, 2027, 0.21, "in force on 30 April 2027"),
            Check("parameter", BASIC_RATE, 2028, 0.20, "prior law after 5 April 2028"),
            Check(
                "change",
                "income_tax",
                2027,
                _uplift(2027, 0.21),
                INCOME_UPLIFT_ORACLE,
                0.005,
            ),
            Check("change", "income_tax", 2028, 0.0, "the change has ended", 0.005),
        ),
    ),
    Case(
        id="extended_freeze",
        title="Personal allowance and basic rate limit frozen to 2033-34",
        changes=(
            Change(
                PERSONAL_ALLOWANCE, _date("2031-04-06"), 12_570, _date("2034-04-05")
            ),
            Change(BASIC_RATE_LIMIT, _date("2031-04-06"), 37_700, _date("2034-04-05")),
        ),
        household=adult(),
        checks=tuple(
            check
            for year in (2031, 2032, 2033)
            for check in (
                Check("parameter", PERSONAL_ALLOWANCE, year, 12_570, "frozen"),
                Check("parameter", BASIC_RATE_LIMIT, year, 37_700, "frozen"),
                Check(
                    "parameter",
                    LOWER_PROFITS_LIMIT,
                    year,
                    12_570,
                    "aligned with the allowance",
                ),
                Check(
                    "parameter",
                    UPPER_PROFITS_LIMIT,
                    year,
                    50_270,
                    "allowance + basic rate limit",
                ),
                Check(
                    "parameter",
                    PRIMARY_THRESHOLD,
                    year,
                    weekly(12_570),
                    "12,570 / 52, to the penny",
                ),
                Check(
                    "parameter",
                    UPPER_EARNINGS_LIMIT,
                    year,
                    weekly(50_270),
                    "50,270 / 52, to the penny",
                ),
                Check(
                    "change",
                    "income_tax",
                    year,
                    _freeze_change(year),
                    "basic rate x (current law's allowance - 12,570)",
                    0.005,
                ),
            )
        )
        + (
            Check(
                "parameter",
                PERSONAL_ALLOWANCE,
                2034,
                _baseline_value(PERSONAL_ALLOWANCE, 2034),
                "contract 1.0.0: prior law's projected path resumes",
            ),
            Check(
                "parameter",
                PERSONAL_ALLOWANCE,
                2034,
                _statutory_resumption(PERSONAL_ALLOWANCE),
                "ITA 2007 s57 from the frozen £12,570 with 2034's September CPI rise",
                pending=PRIOR_LAW_DECISION,
            ),
            Check(
                "parameter",
                BASIC_RATE_LIMIT,
                2034,
                _statutory_resumption(BASIC_RATE_LIMIT),
                "ITA 2007 s21 from the frozen £37,700 with 2034's September CPI rise",
                pending=PRIOR_LAW_DECISION,
            ),
        ),
    ),
    Case(
        id="april_benefit_uprating",
        title="UC single 25+ standard allowance £500 from April 2027, £520 from April 2028",
        changes=(
            Change(UC_SINGLE_OLD, _date("2027-04-06"), 500, _date("2028-04-05")),
            Change(UC_SINGLE_OLD, _date("2028-04-06"), 520),
        ),
        household=adult(),
        checks=(
            Check("variable", "uc_standard_allowance", 2027, 6_000.0, "£500 x 12"),
            Check("variable", "uc_standard_allowance", 2028, 6_240.0, "£520 x 12"),
            Check(
                "variable",
                "uc_standard_allowance",
                2029,
                6_240.0,
                "held from April 2028",
            ),
            Check("change", "uc_standard_allowance", 2026, 0.0, "before the change"),
        ),
    ),
    Case(
        id="bounded_change_on_uprated_benefit",
        title="UC single 25+ standard allowance £500 for 2027-28 only",
        changes=(Change(UC_SINGLE_OLD, _date("2027-04-06"), 500, _date("2028-04-05")),),
        household=adult(),
        checks=(
            Check("variable", "uc_standard_allowance", 2027, 6_000.0, "£500 x 12"),
            Check(
                "change",
                "uc_standard_allowance",
                2028,
                0.0,
                "prior law's uprated path resumes",
            ),
            Check(
                "change",
                "uc_standard_allowance",
                2030,
                0.0,
                "prior law's uprated path resumes",
            ),
        ),
    ),
    Case(
        id="uc_award_follows_the_standard_allowance",
        title="A claimant with no income is awarded the reformed standard allowance",
        changes=(Change(UC_SINGLE_OLD, _date("2027-04-06"), 500, _date("2028-04-05")),),
        household=adult(0),
        checks=(
            Check(
                "variable",
                "universal_credit",
                2027,
                6_000.0,
                "with no income or other elements, the award is the standard "
                "allowance: £500 x 12",
                0.01,
            ),
            Check("change", "universal_credit", 2026, 0.0, "before the change", 0.01),
            Check(
                "change",
                "universal_credit",
                2028,
                0.0,
                "prior law's uprated path resumes",
                0.01,
            ),
        ),
    ),
    Case(
        id="new_state_pension_rate",
        title="New State Pension £280 a week for 2027-28",
        changes=(
            Change(NEW_STATE_PENSION, _date("2027-04-06"), 280.0, _date("2028-04-05")),
        ),
        household=Household(
            people=(
                {
                    "age": 68,
                    "state_pension_type": "NEW",
                    # Above the full rate, so the person gets the full rate.
                    "state_pension_reported": 20_000,
                },
            )
        ),
        checks=(
            Check(
                "variable",
                "new_state_pension",
                2027,
                14_560.0,
                "the full weekly rate x 52: £280 x 52",
                0.01,
            ),
            Check("change", "new_state_pension", 2026, 0.0, "before the change", 0.01),
        ),
    ),
    Case(
        id="mid_year_blended_rate",
        title="CGT basic rate 20% from 30 October 2027",
        changes=(Change(CGT_BASIC_RATE, _date("2027-10-30"), 0.20),),
        household=adult(),
        checks=(
            Check(
                "parameter",
                CGT_BASIC_RATE,
                2027,
                fiscal_year_average(
                    [(_date("2024-10-30"), 0.18), (_date("2027-10-30"), 0.20)], 2027
                ),
                "day-weighted: 207 days at 18% and 159 at 20% of 366",
                1e-12,
            ),
            Check("parameter", CGT_BASIC_RATE, 2028, 0.20, "in force all year"),
            Check("parameter", CGT_BASIC_RATE, 2026, 0.18, "before the change"),
        ),
    ),
    Case(
        id="september_cpi_moves_indexed_thresholds",
        title="A 5% September 2030 CPI rise indexes the 2031-32 thresholds",
        changes=(
            Change(CPI_SEPTEMBER, _date("2030-09-01"), 0.05, _date("2031-08-31")),
        ),
        household=adult(),
        checks=(
            Check(
                "parameter",
                PERSONAL_ALLOWANCE,
                2031,
                s57_personal_allowance(12_570, 0.05),
                "ITA 2007 s57(3)",
            ),
            Check(
                "parameter",
                BASIC_RATE_LIMIT,
                2031,
                s21_basic_rate_limit(37_700, 0.05),
                "ITA 2007 s21(3)",
            ),
            Check(
                "parameter",
                PRIMARY_THRESHOLD,
                2031,
                weekly(s57_personal_allowance(12_570, 0.05)),
                "aligned with the allowance, weekly",
            ),
        ),
        routes=COUNTRY_ROUTES,
    ),
    Case(
        id="uc_rebalancing_reform_after_data_load",
        title="Protected LCWRA amount £500 a month for 2027-28",
        changes=(
            Change(PROTECTED_LCWRA, _date("2027-04-06"), 500.0, _date("2028-04-05")),
        ),
        household=adult(0, uc_limited_capability_for_WRA=True),
        checks=(Check("variable", "uc_LCWRA_element", 2027, 6_000.0, "£500 x 12"),),
    ),
    Case(
        id="structural_switch",
        title="Marriage allowance without its income condition",
        changes=(
            Change(MA_INCOME_CONDITION, _date("2025-01-01"), True, _date("2030-12-31")),
        ),
        household=Household(
            people=(
                {"age": 40, "employment_income": 80_000},
                {"age": 40, "employment_income": 0},
            ),
            benunit={"is_married": True},
        ),
        checks=(
            Check(
                "variable",
                "marriage_allowance",
                2026,
                1_260.0,
                "10% of the £12,570 allowance, rounded up to £10 (ITA 2007 s55B)",
            ),
        ),
    ),
    Case(
        id="baseline_vat_is_current_law",
        title="VAT standard rate 22% from 2026-27 (#2188)",
        changes=(Change(VAT_STANDARD_RATE, _date("2026-01-01"), 0.22),),
        household=Household(
            people=({"age": 40},),
            household={
                "full_rate_vat_consumption": 10_000,
                "reduced_rate_vat_consumption": 0,
            },
        ),
        checks=(
            Check(
                "baseline_equals",
                "baseline_vat",
                2026,
                "vat",
                "baseline_vat is the unreformed vat",
            ),
        ),
        routes=COUNTRY_ROUTES + ("wrapper.household",),
    ),
    Case(
        id="unknown_path",
        title="A parameter no certified model defines",
        changes=(
            Change("gov.budget_2026.new_credit.amount", _date("2027-04-06"), 500),
        ),
        household=adult(),
        expect_error="new_credit",
    ),
    # Reading cases: each route's documented key reading.
    Case(
        id="reading_bare_year_dict",
        title="A bare-year policyengine-uk dict key is that fiscal year only",
        changes=(),
        household=adult(),
        routes=("country.reform_dict",),
        representations={"country.reform_dict": {BASIC_RATE: {"2027": 0.21}}},
        checks=(
            Check("parameter", BASIC_RATE, 2027, 0.21, "fiscal year 2027"),
            Check("parameter", BASIC_RATE, 2028, 0.20, "that year only"),
        ),
    ),
    Case(
        id="reading_bare_year_reform_from_dict",
        title="Reform.from_dict reads a bare year as from 1 January on",
        changes=(),
        household=adult(),
        routes=("country.reform_from_dict",),
        representations={"country.reform_from_dict": {BASIC_RATE: {"2027": 0.21}}},
        checks=(
            Check("parameter", BASIC_RATE, 2026, 0.20, "before 1 January 2027"),
            Check("parameter", BASIC_RATE, 2027, 0.21, "from 1 January 2027"),
            Check("parameter", BASIC_RATE, 2028, 0.21, "onwards"),
        ),
    ),
    Case(
        id="reading_single_day_dict",
        title="A single-day policyengine-uk dict key overrides one day",
        changes=(),
        household=adult(),
        routes=("country.reform_dict",),
        representations={"country.reform_dict": {BASIC_RATE: {"2027-04-06": 0.21}}},
        checks=(
            Check("parameter", BASIC_RATE, 2027, 0.20, "one day is not 30 April"),
            Check("parameter", BASIC_RATE, 2028, 0.20, "one day only"),
        ),
    ),
    Case(
        id="reading_effective_dates_reverse_order",
        title="Effective dates given latest first",
        changes=(),
        household=adult(),
        routes=WRAPPER_ROUTES,
        representations={
            "wrapper.household": {
                UC_SINGLE_OLD: {"2028-04-06": 520, "2027-04-06": 500}
            },
            "wrapper.policy": {UC_SINGLE_OLD: {"2028-04-06": 520, "2027-04-06": 500}},
        },
        checks=(
            Check("variable", "uc_standard_allowance", 2027, 6_000.0, "£500 x 12"),
            Check("variable", "uc_standard_allowance", 2028, 6_240.0, "£520 x 12"),
        ),
    ),
)


# Representations.


def country_reform_dict(changes: Sequence[Change]) -> dict:
    reform: dict = {}
    for change in changes:
        reform.setdefault(change.path, {})[change.interval_key] = change.value
    return reform


def wrapper_reform_dict(changes: Sequence[Change]) -> dict:
    """Lone dates for changes held from a date, intervals for bounded ones."""
    reform: dict = {}
    for change in changes:
        key = str(change.start) if change.stop is None else change.interval_key
        reform.setdefault(change.path, {})[key] = change.value
    return reform


def represent(case: Case, route: str) -> Any:
    if route in case.representations:
        return case.representations[route]
    if route in COUNTRY_ROUTES:
        return country_reform_dict(case.changes)
    return wrapper_reform_dict(case.changes)


def reform_digest(representation: Any, route: str) -> str:
    payload = json.dumps(
        {"route": route, "reform": representation}, sort_keys=True, default=str
    )
    return hashlib.sha256(payload.encode()).hexdigest()


# Routes.


def _years(case: Case) -> list[int]:
    years = {check.year for check in case.checks}
    return sorted(years) or [2027]


def _situation(household: Household, years: Sequence[int]) -> dict:
    def periodised(values: Mapping[str, Any]) -> dict:
        return {name: {year: value for year in years} for name, value in values.items()}

    people = {
        f"person_{i}": periodised(person) for i, person in enumerate(household.people)
    }
    return {
        "people": people,
        "benunits": {
            "benunit": {"members": list(people), **periodised(household.benunit)}
        },
        "households": {
            "household": {"members": list(people), **periodised(household.household)}
        },
    }


class RouteRun:
    """Values a route produced for a case: reformed and unreformed."""

    def __init__(self):
        self.reformed: dict[tuple[str, str, int], float] = {}
        self.unreformed: dict[tuple[str, str, int], float] = {}
        self.isolation: list[tuple[str, int, float, float]] = []


def _total(values) -> float:
    return float(sum(float(value) for value in values))


class _CountryRoute:
    def __init__(self, route: str):
        self.route = route

    def simulation(self, representation, situation):
        from policyengine_core.reforms import Reform
        from policyengine_uk import Simulation
        from policyengine_uk.utils.scenario import Scenario

        if self.route == "country.reform_dict":
            return Simulation(situation=situation, reform=representation)
        if self.route == "country.scenario_parameter_changes":
            return Simulation(
                situation=situation,
                scenario=Scenario(parameter_changes=representation),
            )
        return Simulation(
            situation=situation,
            reform=Reform.from_dict(representation, country_id="uk"),
        )

    @staticmethod
    def _value(simulation, request: tuple[str, str, int]) -> float:
        kind, name, year = request
        if kind == "parameter":
            parameter = simulation.tax_benefit_system.parameters.get_child(name)
            return float(parameter(f"{year}-01-01"))
        return _total(simulation.calculate(name, year))

    def run(self, case: Case, representation, cache: dict) -> RouteRun:
        from policyengine_uk import Simulation

        years = _years(case)
        situation = _situation(case.household, years)
        situation_key = json.dumps(situation, sort_keys=True, default=str)
        requests: list[tuple[str, str, int]] = []
        for check in case.checks:
            kind = "parameter" if check.target == "parameter" else "variable"
            requests.append((kind, check.name, check.year))
            if check.target == "baseline_equals":
                requests.append(("variable", check.expected, check.year))
        # Unreformed values are cached, not simulations, so each simulation
        # can be released as soon as its case is done.
        missing = [
            request
            for request in requests
            if (self.route, situation_key, request) not in cache
        ]
        if missing:
            unreformed = Simulation(situation=situation)
            for request in missing:
                cache[(self.route, situation_key, request)] = self._value(
                    unreformed, request
                )
            del unreformed
        reformed = self.simulation(representation, situation)
        baseline = getattr(reformed, "baseline", None)
        run = RouteRun()
        for request in requests:
            run.reformed[request] = self._value(reformed, request)
            run.unreformed[request] = cache[(self.route, situation_key, request)]
            if request[0] == "variable" and baseline is not None:
                run.isolation.append(
                    (
                        request[1],
                        request[2],
                        self._value(baseline, request),
                        run.unreformed[request],
                    )
                )
        return run


class _WrapperHouseholdRoute:
    route = "wrapper.household"

    def _call(self, case: Case, year: int, reform, variables: Sequence[str]):
        import policyengine as pe

        household = case.household
        return pe.uk.calculate_household(
            people=[dict(person) for person in household.people],
            benunit=dict(household.benunit),
            household=dict(household.household),
            year=year,
            reform=reform,
            extra_variables=list(variables),
        )

    def run(self, case: Case, representation, cache: dict) -> RouteRun:
        run = RouteRun()
        by_year: dict[int, set[str]] = {}
        for check in case.checks:
            if check.target == "parameter":
                continue
            by_year.setdefault(check.year, set()).add(check.name)
            if check.target == "baseline_equals":
                by_year[check.year].add(check.expected)
        for year, names in by_year.items():
            names = sorted(names)
            reformed = self._call(case, year, representation, names)
            key = (self.route, _household_key(case.household), year, tuple(names))
            if key not in cache:
                cache[key] = self._call(case, year, None, names)
            unreformed = cache[key]
            for name in names:
                run.reformed[("variable", name, year)] = _result_total(reformed, name)
                run.unreformed[("variable", name, year)] = _result_total(
                    unreformed, name
                )
        return run


def _household_key(household: Household) -> str:
    return json.dumps(
        {
            "people": list(household.people),
            "benunit": dict(household.benunit),
            "household": dict(household.household),
        },
        sort_keys=True,
        default=str,
    )


def _result_total(result, name: str) -> float:
    total = 0.0
    found = False
    for entity in ("person", "benunit", "household"):
        rows = result[entity] if entity in result else []
        if isinstance(rows, Mapping):
            rows = [rows]
        for row in rows:
            if name in row:
                total += float(row[name])
                found = True
    if not found:
        raise KeyError(f"{name} is not in the household result")
    return total


class _WrapperPolicyRoute:
    route = "wrapper.policy"

    def _dataset(self, household: Household, year: int):
        import pandas as pd
        from microdf import MicroDataFrame

        from policyengine.tax_benefit_models.uk.datasets import (
            PolicyEngineUKDataset,
            UKYearData,
        )

        people = [dict(person) for person in household.people]
        person = pd.DataFrame(people)
        person["person_id"] = range(1, len(people) + 1)
        person["person_benunit_id"] = 1
        person["person_household_id"] = 1
        person["person_weight"] = 1.0
        benunit = pd.DataFrame(
            [{"benunit_id": 1, "benunit_weight": 1.0, **household.benunit}]
        )
        # A UK dataset's household table carries a region (the run fails
        # without one) and housing costs; these are neutral defaults.
        household_frame = pd.DataFrame(
            [
                {
                    "household_id": 1,
                    "household_weight": 1.0,
                    "region": "LONDON",
                    "tenure_type": "OWNED_OUTRIGHT",
                    "rent": 0.0,
                    "council_tax": 0.0,
                    **household.household,
                }
            ]
        )
        return PolicyEngineUKDataset(
            id=f"budget-reform-contract-{year}",
            name="Budget reform contract household",
            description="One household for the Budget reform contract",
            filepath=None,
            year=year,
            data=UKYearData(
                person=MicroDataFrame(person, weights="person_weight"),
                benunit=MicroDataFrame(benunit, weights="benunit_weight"),
                household=MicroDataFrame(household_frame, weights="household_weight"),
            ),
        )

    def _run(self, dataset, policy, variables: Mapping[str, Sequence[str]]):
        from policyengine.core import Simulation
        from policyengine.tax_benefit_models.uk import uk_latest

        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=uk_latest,
            policy=policy,
            extra_variables={
                entity: list(names) for entity, names in variables.items()
            },
        )
        simulation.run()
        return simulation.output_dataset.data

    def run(self, case: Case, representation, cache: dict) -> RouteRun:
        from policyengine.tax_benefit_models.common.reform import (
            compile_reform_to_policy,
        )
        from policyengine.tax_benefit_models.uk import uk_latest

        run = RouteRun()
        by_year: dict[int, set[str]] = {}
        for check in case.checks:
            if check.target in ("parameter", "baseline_equals"):
                continue
            by_year.setdefault(check.year, set()).add(check.name)
        for year, names in by_year.items():
            variables = _by_entity(sorted(names))
            policy = compile_reform_to_policy(
                representation, year=year, model_version=uk_latest
            )
            dataset = self._dataset(case.household, year)
            reformed = self._run(dataset, policy, variables)
            key = (
                self.route,
                _household_key(case.household),
                year,
                tuple(sorted(names)),
            )
            if key not in cache:
                cache[key] = self._run(
                    self._dataset(case.household, year), None, variables
                )
            unreformed = cache[key]
            for entity, entity_names in variables.items():
                for name in entity_names:
                    run.reformed[("variable", name, year)] = _total(
                        getattr(reformed, entity)[name]
                    )
                    run.unreformed[("variable", name, year)] = _total(
                        getattr(unreformed, entity)[name]
                    )
        return run


def _by_entity(names: Sequence[str]) -> dict[str, list[str]]:
    from policyengine_uk.system import system

    grouped: dict[str, list[str]] = {}
    for name in names:
        grouped.setdefault(system.variables[name].entity.key, []).append(name)
    return grouped


def _route(route: str):
    if route in COUNTRY_ROUTES:
        return _CountryRoute(route)
    if route == "wrapper.household":
        return _WrapperHouseholdRoute()
    if route == "wrapper.policy":
        return _WrapperPolicyRoute()
    raise ValueError(f"Unknown route {route!r}; expected one of {ROUTES}.")


# Memory.

# policyengine-core registers each tax-benefit system's variable files in
# sys.modules as "<id(system)>_<hash>_<file>" and never removes them
# (PolicyEngine/policyengine-core#520), about 10 MB per simulation. The
# contract builds hundreds of simulations, so it drops the modules of systems
# that no longer exist, as policyengine-uk's test suite does.
_VARIABLE_MODULE_NAME = re.compile(r"(\d+)_-?\d+_")


def release_dead_variable_modules(max_owners: int = 8) -> int:
    owners: dict[str, list[str]] = {}
    for name in list(sys.modules):
        match = _VARIABLE_MODULE_NAME.match(name)
        if match:
            owners.setdefault(match.group(1), []).append(name)
    if len(owners) <= max_owners:
        return 0
    from policyengine_core.taxbenefitsystems import TaxBenefitSystem

    gc.collect()
    live = {
        str(id(obj)) for obj in gc.get_objects() if isinstance(obj, TaxBenefitSystem)
    }
    released = 0
    for owner, names in owners.items():
        if owner not in live:
            for name in names:
                if sys.modules.pop(name, None) is not None:
                    released += 1
    return released


# Evaluation.


def _baseline_parameter_reader() -> Callable[[str, int], float]:
    from policyengine_uk.system import system

    def read(path: str, year: int) -> float:
        return float(system.parameters.get_child(path)(f"{year}-01-01"))

    return read


def _row(case: Case, route: str, digest: Optional[str], **fields) -> dict:
    row = {"case_id": case.id, "route": route, "reform_digest": digest}
    row.update(fields)
    return row


def _close(actual: float, expected: float, tolerance: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= tolerance


def evaluate_case(case: Case, route: str, cache: Optional[dict] = None) -> list[dict]:
    """Run one case through one route; one report row per check."""
    cache = {} if cache is None else cache
    if route in UNSUPPORTED_ROUTES:
        return [
            _row(
                case,
                route,
                None,
                check=None,
                status=UNSUPPORTED,
                reason=UNSUPPORTED_ROUTES[route],
            )
        ]
    representation = represent(case, route)
    digest = reform_digest(representation, route)
    context = Context(_baseline_parameter_reader())
    if case.expect_error is not None:
        try:
            _route(route).run(
                Case(
                    case.id,
                    case.title,
                    case.changes,
                    case.household,
                    (Check("change", "income_tax", 2027, 0.0, ""),),
                ),
                representation,
                cache,
            )
        except Exception as error:  # noqa: BLE001 - any rejection is reported
            matched = re.search(case.expect_error, str(error)) is not None
            return [
                _row(
                    case,
                    route,
                    digest,
                    check="rejected",
                    status=PASS if matched else FAIL,
                    expected=f"an error matching {case.expect_error!r}",
                    actual=f"{type(error).__name__}: {error}"[:500],
                )
            ]
        return [
            _row(
                case,
                route,
                digest,
                check="rejected",
                status=FAIL,
                expected=f"an error matching {case.expect_error!r}",
                actual="accepted",
            )
        ]
    try:
        run = _route(route).run(case, representation, cache)
    except Exception as error:  # noqa: BLE001 - a crash is a contract error
        return [
            _row(
                case,
                route,
                digest,
                check=None,
                status=ERROR,
                detail="".join(
                    traceback.format_exception_only(type(error), error)
                ).strip()[:1000],
            )
        ]
    rows = []
    for check in case.checks:
        label = f"{check.target}:{check.name}:{check.year}"
        if check.target == "parameter" and route not in COUNTRY_ROUTES:
            rows.append(
                _row(
                    case,
                    route,
                    digest,
                    check=label,
                    status=UNSUPPORTED,
                    reason="this route exposes outputs, not parameter values",
                )
            )
            continue
        if check.target == "baseline_equals" and route == "wrapper.policy":
            rows.append(
                _row(
                    case,
                    route,
                    digest,
                    check=label,
                    status=UNSUPPORTED,
                    reason="the policy route's output dataset holds the reformed run only",
                )
            )
            continue
        try:
            if check.target == "baseline_equals":
                actual = run.reformed[("variable", check.name, check.year)]
                expected = run.unreformed[("variable", check.expected, check.year)]
            elif check.target == "change":
                key = ("variable", check.name, check.year)
                actual = run.reformed[key] - run.unreformed[key]
                expected = (
                    check.expected(context)
                    if callable(check.expected)
                    else check.expected
                )
            else:
                kind = "parameter" if check.target == "parameter" else "variable"
                actual = run.reformed[(kind, check.name, check.year)]
                expected = (
                    check.expected(context)
                    if callable(check.expected)
                    else check.expected
                )
        except Exception as error:  # noqa: BLE001
            rows.append(
                _row(
                    case,
                    route,
                    digest,
                    check=label,
                    status=PENDING if check.pending is not None else ERROR,
                    decision_id=check.pending,
                    detail=repr(error)[:500],
                )
            )
            continue
        passed = _close(actual, float(expected), check.tolerance)
        status = PASS if passed else FAIL
        if check.pending is not None:
            status = PENDING
        rows.append(
            _row(
                case,
                route,
                digest,
                check=label,
                status=status,
                expected=float(expected),
                actual=actual,
                oracle=check.oracle,
                decision_id=check.pending,
                holds=passed if check.pending is not None else None,
            )
        )
    for name, year, from_baseline, unreformed in run.isolation:
        rows.append(
            _row(
                case,
                route,
                digest,
                check=f"baseline_isolation:{name}:{year}",
                status=PASS if from_baseline == unreformed else FAIL,
                expected=unreformed,
                actual=from_baseline,
                oracle="the reformed simulation's baseline equals an unreformed simulation",
            )
        )
    return rows


# Properties: bounded sampling.

SAMPLED_PARAMETERS = {
    BASIC_RATE: (False, (0.15, 0.19, 0.21, 0.25)),
    UC_SINGLE_OLD: (False, (350.0, 480.0, 512.5, 600.0)),
    PERSONAL_ALLOWANCE: (False, (11_000, 12_570, 15_000)),
    CGT_BASIC_RATE: (True, (0.1, 0.2, 0.24)),
}
SAMPLED_YEARS = range(2025, 2036)


def _sampled_change(rng: random.Random) -> Change:
    path = rng.choice(sorted(SAMPLED_PARAMETERS))
    _, values = SAMPLED_PARAMETERS[path]
    start = datetime.date(2025, 6, 1) + datetime.timedelta(
        days=rng.randrange(0, 8 * 365)
    )
    stop = (
        None
        if rng.random() < 0.5
        else start + datetime.timedelta(days=rng.randrange(0, 1500))
    )
    return Change(path, start, rng.choice(values), stop)


def expected_annual(
    change: Change, year: int, baseline: Callable[[str, int], float]
) -> float:
    """The annual value a single change gives, under contract 1.0.0.

    Prior law is current law's annual value outside the change. Blended
    parameters are sampled only from 2025 on, where current law holds one
    value through each fiscal year, so each day of the year takes the
    change's value inside the change and prior law's outside it.
    """
    blend, _ = SAMPLED_PARAMETERS[change.path]
    stop = change.stop or FLAT_STOP
    prior = baseline(change.path, year)
    if not blend:
        sample = datetime.date(year, 4, 30)
        return change.value if change.start <= sample <= stop else prior
    day = datetime.date(year, 4, 6)
    end = datetime.date(year + 1, 4, 6)
    total = 0.0
    days = 0
    while day < end:
        total += change.value if change.start <= day <= stop else prior
        days += 1
        day += datetime.timedelta(days=1)
    return total / days


def _property_annual_values(change: Change, routes: Sequence[str], cache: dict) -> None:
    baseline = _baseline_parameter_reader()
    representation = country_reform_dict([change])
    for route in routes:
        simulation = _CountryRoute(route).simulation(
            representation, _situation(adult(), [2027])
        )
        for year in SAMPLED_YEARS:
            actual = float(
                simulation.tax_benefit_system.parameters.get_child(change.path)(
                    f"{year}-01-01"
                )
            )
            expected = expected_annual(change, year, baseline)
            assert abs(actual - expected) <= 1e-9, (
                route,
                change,
                year,
                actual,
                expected,
            )


def _property_routes_agree(
    change: Change, income: int, routes: Sequence[str], cache: dict
) -> None:
    household = adult(income)
    case = Case(
        "sampled",
        "sampled",
        (change,),
        household,
        tuple(
            Check("change", "income_tax", year, 0.0, "") for year in (2026, 2028, 2031)
        ),
    )
    results = {}
    for route in routes:
        run = _route(route).run(case, represent(case, route), cache)
        results[route] = {key: run.reformed[key] for key in run.reformed}
        for name, year, from_baseline, unreformed in run.isolation:
            assert from_baseline == unreformed, (route, name, year)
    first = next(iter(results.values()))
    for route, values in results.items():
        for key, value in values.items():
            assert abs(value - first[key]) <= 1e-6, (route, key, value, first[key])


PROPERTIES = {
    "annual_values_match_the_oracle": "Random single changes on the country routes give the annual values of an independent fiscal-year annualisation.",
    "routes_agree_and_baselines_hold": "Random changes give the same household income tax on every in-process route, and leave each route's baseline unchanged.",
}


def run_property(
    property_id: str, routes: Sequence[str], seed: int, max_examples: int, cache: dict
) -> dict:
    if max_examples <= 0:
        return {
            "property_id": property_id,
            "status": UNSUPPORTED,
            "examples_run": 0,
            "reason": "max_examples is 0, so no examples were requested",
        }
    country = [route for route in routes if route in COUNTRY_ROUTES]
    in_process = [route for route in routes if route not in UNSUPPORTED_ROUTES]
    if property_id == "annual_values_match_the_oracle":
        if not country:
            return {
                "property_id": property_id,
                "status": UNSUPPORTED,
                "examples_run": 0,
                "reason": "needs a country route",
            }

        def check(change, income):
            _property_annual_values(change, country, cache)

    else:
        if len(in_process) < 2:
            return {
                "property_id": property_id,
                "status": UNSUPPORTED,
                "examples_run": 0,
                "reason": "needs two in-process routes",
            }

        def check(change, income):
            _property_routes_agree(change, income, in_process, cache)

    examples = 0
    try:
        from hypothesis import HealthCheck, Phase, given, settings
        from hypothesis import seed as hypothesis_seed
        from hypothesis import strategies as st

        engine = "hypothesis"

        @hypothesis_seed(seed)
        @settings(
            max_examples=max_examples,
            deadline=None,
            database=None,
            suppress_health_check=list(HealthCheck),
            # Shrinking reruns a failing example many times; each example
            # builds several simulations, so it is left out to bound runtime.
            phases=[Phase.explicit, Phase.generate],
        )
        @given(
            change=st.randoms(use_true_random=False).map(_sampled_change),
            income=st.integers(0, 150_000),
        )
        def sampled(change, income):
            nonlocal examples
            examples += 1
            check(change, income)
            release_dead_variable_modules()

        sampled()
        return {
            "property_id": property_id,
            "engine": engine,
            "examples_run": examples,
            "status": PASS,
        }
    except ImportError:
        rng = random.Random(seed)
        for _ in range(max_examples):
            change = _sampled_change(rng)
            income = rng.randrange(0, 150_001)
            examples += 1
            try:
                check(change, income)
                release_dead_variable_modules()
            except AssertionError as failure:
                return {
                    "property_id": property_id,
                    "engine": "random",
                    "examples_run": examples,
                    "status": FAIL,
                    "counterexample": {
                        "change": repr(change),
                        "income": income,
                        "detail": str(failure),
                    },
                }
        return {
            "property_id": property_id,
            "engine": "random",
            "examples_run": examples,
            "status": PASS,
        }
    except AssertionError as failure:
        return {
            "property_id": property_id,
            "engine": "hypothesis",
            "examples_run": examples,
            "status": FAIL,
            "counterexample": str(failure)[:2000],
        }
    except Exception as error:  # noqa: BLE001
        return {
            "property_id": property_id,
            "engine": "hypothesis",
            "examples_run": examples,
            "status": ERROR,
            "detail": repr(error)[:2000],
        }


# Entry point.


def _versions() -> dict:
    versions = {}
    for package in ("policyengine", "policyengine-uk", "policyengine-core"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run_budget_reform_contract(
    *,
    routes: Optional[Sequence[str]] = None,
    dataset_path: Optional[str] = None,
    seed: int = 0,
    max_examples: int = 20,
    cases: Optional[Sequence[str]] = None,
) -> dict:
    """Run the UK Budget reform contract and return its JSON report.

    Args:
        routes: Route ids to run (see :data:`ROUTES`). None runs every route;
            ``api.sim_api`` reports ``unsupported`` with its reason.
        dataset_path: A certified UK dataset file. When given, the population
            checks also run on a deterministic subsample of it.
        seed: Seed for the sampled properties.
        max_examples: Examples per sampled property.
        cases: Case ids to run; None runs every case.
    """
    selected_routes = list(routes) if routes is not None else list(ROUTES)
    unknown = [route for route in selected_routes if route not in ROUTES]
    if unknown:
        raise ValueError(f"Unknown routes {unknown}; expected some of {ROUTES}.")
    selected_cases = [case for case in CASES if cases is None or case.id in cases]
    cache: dict = {}
    rows: list[dict] = []
    for case in selected_cases:
        for route in selected_routes:
            if case.routes is not None and route not in case.routes:
                continue
            rows.extend(evaluate_case(case, route, cache))
            release_dead_variable_modules()
    properties = [
        run_property(property_id, selected_routes, seed, max_examples, cache)
        for property_id in PROPERTIES
    ]
    population: list[dict] = []
    if dataset_path is not None:
        from policyengine.tax_benefit_models.uk.budget_reform_population import (
            run_population_checks,
        )

        population = run_population_checks(dataset_path, selected_routes, seed)
    summary = {status: 0 for status in (PASS, FAIL, ERROR, UNSUPPORTED, PENDING)}
    for row in rows + properties + population:
        summary[row["status"]] = summary.get(row["status"], 0) + 1
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "prior_law_option": PRIOR_LAW_OPTION,
        "versions": _versions(),
        "dataset": (
            {"path": dataset_path, "sha256": _sha256(dataset_path)}
            if dataset_path is not None
            else None
        ),
        "routes": selected_routes,
        "seed": seed,
        "max_examples": max_examples,
        "cases": rows,
        "properties": properties,
        "population": population,
        "summary": summary,
        "holds": summary[FAIL] == 0 and summary[ERROR] == 0,
    }
