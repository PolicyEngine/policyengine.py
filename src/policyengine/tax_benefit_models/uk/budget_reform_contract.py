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

Where the timeline states no later value, what prior law is after a change
ends depends on how the parameter's future is made. Contract 2.0.0
(``PRIOR_LAW_OPTION = "statutory"``) records the Budget CI workstream's
call under cos d1344, taken with independent review:

- A threshold indexed from its own previous year (the personal allowance,
  the basic rate limit and the NICs thresholds aligned with them) resumes
  indexation from the changed amount. Income Tax Act 2007 s57(3) Step 1
  multiplies "the allowance ... for the previous tax year" and s21(3) Step 1
  increases "the basic rate limit for the previous tax year"; freezes are
  legislated by fixing the amount and disapplying the indexation for named
  years (Finance Act 2021 s5), so the frozen amount is indexed after them.
  Returning to the path the threshold would have taken without the change,
  contract 1.0.0's reading, has no statutory basis.
- An amount uprated from an index (benefit and pension rates) returns to its
  uprated path, as contract 1.0.0 expected. That reading is not settled:
  freezes of such amounts resumed from the frozen amount (Welfare Reform and
  Work Act 2016 s11), while a period-limited modification reverts (SI
  2020/371 reg 3). It is open in policyengine-uk#2430; the contract's
  checks on it stay as they were until that is decided.

``Check.pending`` remains for open calls. No check waits on d1344 now; the
default capital gains response's checks wait on policyengine-uk#2396 (see
Behavioural responses).

Behavioural responses
---------------------

A case about statutory arithmetic holds capital gains realisations fixed: it
sets both elasticity conventions to zero and the separate Business Asset
Disposal Relief elasticity off (:func:`capital_gains_response` with an
elasticity of 0), so its expected values hold whatever response
policyengine-uk applies by default. A case about the response sets its
elasticity, and expects realised gains scaled by
``((1 - t1) / (1 - t0)) ** elasticity``, where ``t0`` and ``t1`` are the
marginal rates on the gains without and with the reform. Contract 1.1.0
added both, and a case with no response settings that shows the default
response policyengine-uk applies. Its checks expect the retention-rate
elasticity of 1 that policyengine-uk#2396 makes the default, and carry
``pending`` until policyengine.py pins a release with it. Contract 2.1.0
adds a second default case, for gains partly qualifying for Business Asset
Disposal Relief, which respond at the same elasticity.

Report
------

A JSON-serialisable dict: ``contract_id``, ``contract_version``,
``prior_law_option``, installed ``versions``, the dataset's sha256 when one
is given, ``cases`` (one row per case, route and check, with ``status`` of
``pass``, ``fail``, ``error``, ``unsupported`` or ``pending``),
``properties``, ``population`` and ``summary`` counts. ``cases`` also
holds two run-level rows: ``module_parameters_unchanged`` (policyengine-uk's
shared parameter state, including the cached tree new simulations copy,
still equals its values before the run) and, when no case, property or
population check passed, an ``error`` row with case id ``run``. Any ``fail`` or
``error`` means the contract does not hold.

Isolation
---------

Expected values read a copy of current law's parameters taken before any
reform runs. Every route's unreformed reference is built before its reform,
and after each reform a fresh unreformed simulation must reproduce it
(``unreformed_after_reform`` rows); the country routes also check each
reformed simulation's own baseline (``baseline_isolation`` rows).
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
from dataclasses import dataclass, field, replace
from decimal import ROUND_CEILING, Decimal
from typing import Any, Optional, Union

CONTRACT_ID = "policyengine-uk/budget-reform-contract"
CONTRACT_VERSION = "2.1.0"
PRIOR_LAW_OPTION = "statutory"
# The cos decision under which the prior-law call was taken.
PRIOR_LAW_DECISION = "d1344"
# Finance Act 2021 s5, as amended by Finance Act 2026 s10, fixes the
# personal allowance and basic rate limit for 2022-23 to 2030-31.
LAST_FROZEN_TAX_YEAR = 2030
# The capital gains response default: policyengine-uk#2396 makes it a
# retention-rate elasticity of 1. Its checks gate once policyengine.py pins it.
DEFAULT_RESPONSE_DECISION = "policyengine-uk#2396"
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
DIVIDEND_BASIC_RATE = "gov.hmrc.income_tax.rates.dividends[0].rate"
DIVIDEND_ALLOWANCE = "gov.hmrc.income_tax.allowances.dividend_allowance"
PERSONAL_ALLOWANCE = "gov.hmrc.income_tax.allowances.personal_allowance.amount"
BASIC_RATE_LIMIT = "gov.hmrc.income_tax.rates.uk[1].threshold"
UC_SINGLE_OLD = "gov.dwp.universal_credit.standard_allowance.amount.SINGLE_OLD"
NEW_STATE_PENSION = "gov.dwp.state_pension.new_state_pension.amount"
CGT_BASIC_RATE = "gov.hmrc.cgt.basic_rate"
CGT_HIGHER_RATE = "gov.hmrc.cgt.higher_rate"
CGT_ADDITIONAL_RATE = "gov.hmrc.cgt.additional_rate"
CGT_BADR_RATE = "gov.hmrc.cgt.badr.rate"
CGT_ANNUAL_EXEMPT_AMOUNT = "gov.hmrc.cgt.annual_exempt_amount"
CGT_RESPONSES = "gov.simulation.capital_gains_responses"
CGT_ELASTICITY = f"{CGT_RESPONSES}.elasticity"
CGT_MTR_ELASTICITY = f"{CGT_RESPONSES}.mtr_elasticity"
CGT_SEPARATE_BADR_ELASTICITY = f"{CGT_RESPONSES}.separate_badr_elasticity"
VAT_STANDARD_RATE = "gov.hmrc.vat.standard_rate"
VAT_COVERAGE = "gov.simulation.microdata_vat_coverage"
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
    reform every route must reject. ``modifier`` holds changes a simulation
    modifier writes onto the annualised parameters, combined with the
    route's reform in one scenario or policy: modifier first when
    ``modifier_first``, else reform first.
    """

    id: str
    title: str
    changes: tuple[Change, ...]
    household: Household
    checks: tuple[Check, ...] = ()
    expect_error: Optional[str] = None
    routes: Optional[tuple[str, ...]] = None
    representations: Mapping[str, Any] = field(default_factory=dict)
    modifier: tuple[Change, ...] = ()
    modifier_first: bool = True


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


def _resumed_after_freeze(path: str, year: int) -> Callable[[Context], float]:
    """A threshold frozen to 2033-34, indexed from the frozen amount after it.

    ITA 2007 s57(3) for the personal allowance and s21(3) for the basic rate
    limit, each year from the year before, with current law's September CPI
    rise for that year.
    """

    def expected(context: Context) -> float:
        allowance, limit = 12_570.0, 37_700.0
        for each in range(2034, year + 1):
            increase = context.baseline(SEPTEMBER_CPI_RISE, each)
            allowance = s57_personal_allowance(allowance, increase)
            limit = s21_basic_rate_limit(limit, increase)
        if path == PERSONAL_ALLOWANCE:
            return allowance
        if path == BASIC_RATE_LIMIT:
            return limit
        if path == LOWER_PROFITS_LIMIT:
            return allowance
        if path == UPPER_PROFITS_LIMIT:
            return allowance + limit
        if path == PRIMARY_THRESHOLD:
            return weekly(allowance)
        if path == UPPER_EARNINGS_LIMIT:
            return weekly(allowance + limit)
        raise ValueError(path)

    return expected


def _resumed_freeze_change(year: int) -> Callable[[Context], float]:
    def expected(context: Context) -> float:
        allowance = _resumed_after_freeze(PERSONAL_ALLOWANCE, year)(context)
        frozen_out = context.baseline(PERSONAL_ALLOWANCE, year) - allowance
        return context.baseline(BASIC_RATE, year) * frozen_out

    return expected


RESUMPTION_ORACLE = (
    "indexed from the frozen amount after the freeze (ITA 2007 s57(3) and "
    "s21(3), the previous tax year's amount; cos d1344), with current law's "
    "September CPI rise"
)


GAINS = 10_000


def _gains_uplift(year: int, share_of_year: float) -> Callable[[Context], float]:
    """Extra CGT on gains taxed wholly at the basic rate, at 20% for part of a year."""

    def expected(context: Context) -> float:
        taxable = GAINS - context.baseline(CGT_ANNUAL_EXEMPT_AMOUNT, year)
        rise = 0.20 - context.baseline(CGT_BASIC_RATE, year)
        return taxable * rise * share_of_year

    return expected


GAINS_UPLIFT_ORACLE = (
    "(£10,000 of gains - the annual exempt amount) x (20% - current rate) x "
    "the share of the tax year at 20%, with realisations held fixed; the "
    "gains sit wholly in the basic rate band, and the exempt amount and "
    "current rate are read from current law"
)


def capital_gains_response(
    start: datetime.date, elasticity: float = 0.0
) -> tuple[Change, ...]:
    """Changes fixing the capital gains realisation response from ``start`` on.

    A retention-rate elasticity of ``elasticity``, no marginal tax rate
    elasticity and no separate Business Asset Disposal Relief elasticity, so
    every gain responds with ``elasticity``. An elasticity of 0 holds
    realisations fixed, whatever response the model applies by default.
    """
    return (
        Change(CGT_ELASTICITY, start, elasticity),
        Change(CGT_MTR_ELASTICITY, start, 0.0),
        Change(CGT_SEPARATE_BADR_ELASTICITY, start, False),
    )


def _response_settings_checks(
    year: int, elasticity: float, oracle: str
) -> tuple[Check, ...]:
    """Checks that each response setting reached the built system: the
    retention-rate elasticity, no marginal tax rate elasticity, and the
    separate relief elasticity off (a switch reads as 0 when off)."""
    return (
        Check("parameter", CGT_ELASTICITY, year, elasticity, oracle),
        Check("parameter", CGT_MTR_ELASTICITY, year, 0.0, oracle),
        Check("parameter", CGT_SEPARATE_BADR_ELASTICITY, year, 0.0, oracle),
    )


def _realised_gains(
    year: int, rate: float, elasticity: float
) -> Callable[[Context], float]:
    """Gains after the realisation response to a basic rate of ``rate``.

    The gains sit wholly in the basic rate band, so the marginal rates on
    them without and with the reform are the two basic rates.
    """

    def expected(context: Context) -> float:
        current = context.baseline(CGT_BASIC_RATE, year)
        return GAINS * ((1 - rate) / (1 - current)) ** elasticity

    return expected


def _gains_response_uplift(
    year: int, rate: float, elasticity: float
) -> Callable[[Context], float]:
    """Extra CGT at a basic rate of ``rate`` all year, after the response."""

    def expected(context: Context) -> float:
        exempt = context.baseline(CGT_ANNUAL_EXEMPT_AMOUNT, year)
        current = context.baseline(CGT_BASIC_RATE, year)
        realised = _realised_gains(year, rate, elasticity)(context)
        return (realised - exempt) * rate - (GAINS - exempt) * current

    return expected


REALISED_GAINS_ORACLE = (
    "£10,000 of gains x ((1 - 20%) / (1 - current rate)) to the power of the "
    "elasticity: the gains sit wholly in the basic rate band, so the marginal "
    "rates on them are the basic rates; the current rate is read from "
    "current law"
)

GAINS_RESPONSE_UPLIFT_ORACLE = (
    "(realised gains - the annual exempt amount) x 20% - (£10,000 of gains - "
    "the annual exempt amount) x current rate, with the realised gains above; "
    "the exempt amount and current rate are read from current law"
)

MIXED_GAINS = 50_000
RELIEF_GAINS = 20_000


def _mixed_retention_ratio(year: int, rate: float) -> Callable[[Context], float]:
    """The retention ratio for gains partly qualifying for the relief, when
    the rate on the rest moves to ``rate``.

    The marginal rate on gains is share-weighted across the schedules: the
    relief rate on the qualifying share, the higher rate on the rest. Both
    shares respond to the one change in that rate.
    """

    def expected(context: Context) -> float:
        relief_share = RELIEF_GAINS / MIXED_GAINS
        relief_rate = context.baseline(CGT_BADR_RATE, year)
        before = relief_share * relief_rate + (1 - relief_share) * (
            context.baseline(CGT_HIGHER_RATE, year)
        )
        after = relief_share * relief_rate + (1 - relief_share) * rate
        return (1 - after) / (1 - before)

    return expected


def _scaled(amount: float, ratio, offset: float = 0.0) -> Callable[[Context], float]:
    return lambda context: amount * (ratio(context) + offset)


MIXED_RESPONSE_ORACLE = (
    "£50,000 of gains, £20,000 qualifying for the relief, scaled by "
    "(1 - t1) / (1 - t0), where t0 and t1 are 40% x the relief rate + 60% x "
    "the higher rate (24% now, 45% under the reform); the relief and higher "
    "rates are read from current law"
)

DIVIDENDS = 10_000


def _dividends_and_earnings(
    year: int, rate: Optional[float]
) -> Callable[[Context], float]:
    """The change in tax when dividends are taxed at 8.75%, and earnings at ``rate``.

    The dividends sit wholly in the basic rate band.
    """

    def expected(context: Context) -> float:
        taxed = DIVIDENDS - context.baseline(DIVIDEND_ALLOWANCE, year)
        change = taxed * (0.0875 - context.baseline(DIVIDEND_BASIC_RATE, year))
        if rate is not None:
            change += _uplift(year, rate)(context)
        return change

    return expected


MODIFIER_ORACLE = (
    "(£10,000 of dividends - the dividend allowance) x (8.75% - current "
    "dividend rate), all within the basic rate band"
)


def _modifier_case(case_id: str, modifier_first: bool) -> Case:
    # The modifier and the reform change different parameters, so either
    # order must give the same values: what the two cases check is that
    # neither side is lost however the scenario or policy is assembled.
    order = "then" if modifier_first else "after"
    return Case(
        id=case_id,
        title=(
            "One scenario or policy with a modifier setting the dividend "
            f"rate to 8.75% {order} a basic rate of 21% from 6 April 2027"
        ),
        changes=(Change(BASIC_RATE, _date("2027-04-06"), 0.21),),
        modifier=(Change(DIVIDEND_BASIC_RATE, _date("2026-01-01"), 0.0875),),
        modifier_first=modifier_first,
        household=adult(dividend_income=DIVIDENDS),
        checks=(
            Check(
                "parameter", DIVIDEND_BASIC_RATE, 2026, 0.0875, "set by the modifier"
            ),
            Check(
                "parameter", DIVIDEND_BASIC_RATE, 2027, 0.0875, "set by the modifier"
            ),
            Check("parameter", BASIC_RATE, 2026, 0.20, "before the change"),
            Check("parameter", BASIC_RATE, 2027, 0.21, "in force on 30 April 2027"),
            Check(
                "change",
                "income_tax",
                2026,
                _dividends_and_earnings(2026, None),
                MODIFIER_ORACLE,
                0.005,
            ),
            Check(
                "change",
                "income_tax",
                2027,
                _dividends_and_earnings(2027, 0.21),
                MODIFIER_ORACLE + ", plus " + INCOME_UPLIFT_ORACLE,
                0.005,
            ),
        ),
        # policyengine.uk.calculate_household takes a reform dict only.
        routes=COUNTRY_ROUTES + ("wrapper.policy",),
    )


FULL_RATE_CONSUMPTION = 10_000


def _vat_uplift(year: int, rate: float) -> Callable[[Context], float]:
    def expected(context: Context) -> float:
        rise = rate - context.baseline(VAT_STANDARD_RATE, year)
        return FULL_RATE_CONSUMPTION * rise / context.baseline(VAT_COVERAGE, year)

    return expected


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
        + tuple(
            check
            for year in (2034, 2035)
            for check in (
                *(
                    Check(
                        "parameter",
                        path,
                        year,
                        _resumed_after_freeze(path, year),
                        RESUMPTION_ORACLE,
                    )
                    for path in (
                        PERSONAL_ALLOWANCE,
                        BASIC_RATE_LIMIT,
                        LOWER_PROFITS_LIMIT,
                        UPPER_PROFITS_LIMIT,
                        PRIMARY_THRESHOLD,
                        UPPER_EARNINGS_LIMIT,
                    )
                ),
                Check(
                    "change",
                    "income_tax",
                    year,
                    _resumed_freeze_change(year),
                    "basic rate x (current law's allowance - the allowance "
                    "indexed from the frozen amount)",
                    0.005,
                ),
            )
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
        title="CGT basic rate 20% from 30 October 2027, realisations held fixed",
        changes=(
            Change(CGT_BASIC_RATE, _date("2027-10-30"), 0.20),
            # The case checks the blending of the rate, so the realisation
            # response is off.
            *capital_gains_response(_date("2025-01-01")),
        ),
        # £20,000 of earnings and £10,000 of gains: the taxable gains sit
        # wholly in the basic rate band.
        household=adult(20_000, capital_gains=GAINS),
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
            *_response_settings_checks(2027, 0.0, "set by the case"),
            Check("change", "capital_gains_tax", 2026, 0.0, "before the change", 0.005),
            Check(
                "change",
                "capital_gains_tax",
                2027,
                _gains_uplift(2027, 159 / 366),
                GAINS_UPLIFT_ORACLE + "; 159 of 2027-28's 366 days",
                0.005,
            ),
            Check(
                "change",
                "capital_gains_tax",
                2028,
                _gains_uplift(2028, 1.0),
                GAINS_UPLIFT_ORACLE + "; all of 2028-29",
                0.005,
            ),
        ),
    ),
    Case(
        id="cgt_retention_response",
        title=(
            "CGT basic rate 20% from 6 April 2027, with a retention-rate "
            "elasticity of 1"
        ),
        changes=(
            Change(CGT_BASIC_RATE, _date("2027-04-06"), 0.20),
            *capital_gains_response(_date("2025-01-01"), elasticity=1.0),
        ),
        # As above, the gains sit wholly in the basic rate band, before and
        # after the response.
        household=adult(20_000, capital_gains=GAINS),
        checks=(
            Check("parameter", CGT_BASIC_RATE, 2027, 0.20, "in force all year"),
            *_response_settings_checks(2027, 1.0, "set by the case"),
            Check("change", "capital_gains_tax", 2026, 0.0, "before the change", 0.005),
            Check(
                "variable",
                "capital_gains",
                2026,
                float(GAINS),
                "no rate change before 2027-28, so no response",
                0.01,
            ),
            Check(
                "variable",
                "capital_gains",
                2027,
                _realised_gains(2027, 0.20, 1.0),
                REALISED_GAINS_ORACLE,
                0.01,
            ),
            Check(
                "change",
                "capital_gains_tax",
                2027,
                _gains_response_uplift(2027, 0.20, 1.0),
                GAINS_RESPONSE_UPLIFT_ORACLE,
                0.005,
            ),
        ),
    ),
    Case(
        id="cgt_default_response",
        title=(
            "CGT basic rate 20% from 6 April 2027, at policyengine-uk's "
            "default response"
        ),
        # No response settings, so the report shows the default. The expected
        # values are cgt_retention_response's, the default policyengine-uk#2396
        # sets; they report without gating until policyengine.py pins it.
        changes=(Change(CGT_BASIC_RATE, _date("2027-04-06"), 0.20),),
        household=adult(20_000, capital_gains=GAINS),
        checks=tuple(
            replace(check, pending=DEFAULT_RESPONSE_DECISION)
            for check in (
                *_response_settings_checks(2027, 1.0, "policyengine-uk's default"),
                Check(
                    "variable",
                    "capital_gains",
                    2027,
                    _realised_gains(2027, 0.20, 1.0),
                    REALISED_GAINS_ORACLE + ", at the default elasticity of 1",
                    0.01,
                ),
                Check(
                    "change",
                    "capital_gains_tax",
                    2027,
                    _gains_response_uplift(2027, 0.20, 1.0),
                    GAINS_RESPONSE_UPLIFT_ORACLE + ", at the default elasticity of 1",
                    0.005,
                ),
            )
        ),
    ),
    Case(
        id="cgt_default_response_relief_gains",
        title=(
            "CGT higher and additional rates 45% from 6 April 2027, for gains "
            "partly qualifying for Business Asset Disposal Relief, at the "
            "default response"
        ),
        changes=(
            Change(CGT_HIGHER_RATE, _date("2027-04-06"), 0.45),
            Change(CGT_ADDITIONAL_RATE, _date("2027-04-06"), 0.45),
        ),
        # £80,000 of earnings puts all the gains above the basic rate band;
        # £20,000 of the £50,000 qualify for the relief, whose rate the reform
        # leaves alone. Pending, as cgt_default_response, until the pin.
        household=adult(
            80_000, capital_gains=MIXED_GAINS, capital_gains_badr=RELIEF_GAINS
        ),
        checks=tuple(
            replace(check, pending=DEFAULT_RESPONSE_DECISION)
            for check in (
                Check(
                    "variable",
                    "capital_gains",
                    2027,
                    _scaled(MIXED_GAINS, _mixed_retention_ratio(2027, 0.45)),
                    MIXED_RESPONSE_ORACLE,
                    0.05,
                ),
                # The qualifying gains respond at the same elasticity of 1.
                Check(
                    "variable",
                    "capital_gains_badr_behavioural_response",
                    2027,
                    _scaled(RELIEF_GAINS, _mixed_retention_ratio(2027, 0.45), -1.0),
                    MIXED_RESPONSE_ORACLE + "; the response on the qualifying £20,000",
                    0.05,
                ),
            )
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
                "full_rate_vat_consumption": FULL_RATE_CONSUMPTION,
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
            Check(
                "change",
                "vat",
                2026,
                _vat_uplift(2026, 0.22),
                "£10,000 of full-rate consumption x (22% - current rate), over "
                "the share of consumption the microdata covers; the current "
                "rate and coverage are read from current law",
                0.005,
            ),
        ),
    ),
    # A scenario's parameter changes used to rebuild the parameters after its
    # modifier had run, so whatever the modifier set reverted.
    _modifier_case("modifier_then_parameter_changes", True),
    _modifier_case("parameter_changes_then_modifier", False),
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


def reform_digest(representation: Any, route: str, case: Optional[Case] = None) -> str:
    content: dict = {"route": route, "reform": representation}
    if case is not None and case.modifier:
        content["modifier"] = [
            [change.path, str(change.start), str(change.stop), change.value]
            for change in case.modifier
        ]
        content["modifier_first"] = case.modifier_first
    payload = json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def parameter_modifier(changes: Sequence[Change]) -> Callable:
    """A simulation modifier writing ``changes`` onto the annualised parameters."""

    def modify(simulation):
        from policyengine_core.periods import instant

        parameters = simulation.tax_benefit_system.parameters
        for change in changes:
            parameter = parameters.get_child(change.path)
            if change.stop is None:
                parameter.update(start=instant(str(change.start)), value=change.value)
            else:
                parameter.update(
                    start=instant(str(change.start)),
                    stop=instant(str(change.stop)),
                    value=change.value,
                )
        return simulation

    return modify


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
    """Values a route produced for a case.

    ``unreformed`` values come from simulations built before the reform.
    ``isolation`` pairs the reformed simulation's own baseline with them and
    ``after`` pairs a fresh unreformed simulation built after the reform with
    them, as (name, year, value, unreformed value).
    """

    def __init__(self):
        self.reformed: dict[tuple[str, str, int], float] = {}
        self.unreformed: dict[tuple[str, str, int], float] = {}
        self.isolation: list[tuple[str, int, float, float]] = []
        self.after: list[tuple[str, int, float, float]] = []


def _total(values) -> float:
    return float(sum(float(value) for value in values))


class _CountryRoute:
    def __init__(self, route: str):
        self.route = route

    def simulation(self, representation, situation, case: Optional[Case] = None):
        from policyengine_core.reforms import Reform
        from policyengine_uk import Simulation
        from policyengine_uk.utils.scenario import Scenario

        if case is not None and case.modifier:
            # One scenario carrying the route's reform and the modifier.
            if self.route == "country.reform_dict":
                reform = Scenario.from_reform(representation)
            elif self.route == "country.scenario_parameter_changes":
                reform = Scenario(parameter_changes=representation)
            else:
                reform = Scenario.from_reform(
                    Reform.from_dict(representation, country_id="uk")
                )
            modifier = Scenario(simulation_modifier=parameter_modifier(case.modifier))
            scenario = modifier + reform if case.modifier_first else reform + modifier
            return Simulation(situation=situation, scenario=scenario)
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
        # Two checks can read the same value; request it once.
        requests = list(dict.fromkeys(requests))
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
        reformed = self.simulation(representation, situation, case)
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
        del reformed, baseline
        after = Simulation(situation=situation)
        for request in requests:
            run.after.append(
                (
                    request[1],
                    request[2],
                    self._value(after, request),
                    run.unreformed[request],
                )
            )
        return run


class _WrapperHouseholdRoute:
    route = "wrapper.household"

    def _call(self, case: Case, year: int, reform, variables: Sequence[str]):
        # The module ``policyengine.uk`` names, imported directly: a process
        # that sets POLICYENGINE_SKIP_COUNTRY_IMPORTS, as the qualification
        # scripts do, leaves ``policyengine.uk`` as None.
        from policyengine.tax_benefit_models import uk

        household = case.household
        return uk.calculate_household(
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
        if case.modifier:
            raise ValueError(
                "policyengine.uk.calculate_household takes a reform dict, not a "
                "simulation modifier"
            )
        for year, names in by_year.items():
            names = sorted(names)
            key = (self.route, _household_key(case.household), year, tuple(names))
            # The unreformed reference is built before the reform runs.
            if key not in cache:
                cache[key] = self._call(case, year, None, names)
            unreformed = cache[key]
            reformed = self._call(case, year, representation, names)
            after = self._call(case, year, None, names)
            for name in names:
                request = ("variable", name, year)
                run.reformed[request] = _result_total(reformed, name)
                run.unreformed[request] = _result_total(unreformed, name)
                run.after.append(
                    (name, year, _result_total(after, name), run.unreformed[request])
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
    """The household's total of a variable, read from the variable's entity.

    The household result can also carry a variable aggregated to another
    entity (a benefit-unit award under the household too), so reading every
    entity would count it twice.
    """
    from policyengine_uk.system import system

    entity = system.variables[name].entity.key
    rows = result[entity] if entity in result else []
    if isinstance(rows, Mapping):
        rows = [rows]
    values = [float(row[name]) for row in rows if name in row]
    if not values:
        raise KeyError(f"{name} is not in the household result's {entity} rows")
    return sum(values)


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
            key = (
                self.route,
                _household_key(case.household),
                year,
                tuple(sorted(names)),
            )
            # The unreformed reference is built before the reform runs.
            if key not in cache:
                cache[key] = self._run(
                    self._dataset(case.household, year), None, variables
                )
            unreformed = cache[key]
            policy = compile_reform_to_policy(
                representation, year=year, model_version=uk_latest
            )
            if case.modifier:
                from policyengine.core import Policy

                modifier = Policy(
                    name="modifier",
                    simulation_modifier=parameter_modifier(case.modifier),
                )
                policy = modifier + policy if case.modifier_first else policy + modifier
            reformed = self._run(self._dataset(case.household, year), policy, variables)
            after = self._run(self._dataset(case.household, year), None, variables)
            for entity, entity_names in variables.items():
                for name in entity_names:
                    request = ("variable", name, year)
                    run.reformed[request] = _total(getattr(reformed, entity)[name])
                    run.unreformed[request] = _total(getattr(unreformed, entity)[name])
                    run.after.append(
                        (
                            name,
                            year,
                            _total(getattr(after, entity)[name]),
                            run.unreformed[request],
                        )
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


def reference_parameters():
    """A copy of current law's parameters, taken before any reform runs.

    Expected values read this copy, so a reform that leaks into the shared
    system cannot move the reference it is checked against.
    """
    from policyengine_uk.system import system

    return system.parameters.clone()


def parameter_reader(parameters) -> Callable[[str, int], float]:
    def read(path: str, year: int) -> float:
        return float(parameters.get_child(path)(f"{year}-01-01"))

    return read


def _baseline_parameter_reader() -> Callable[[str, int], float]:
    return parameter_reader(reference_parameters())


def _frozen(value: Any) -> str:
    """A value as text, so a list or dict changed in place still shows.

    JSON where it can be (key order ignored); otherwise ``repr``, so an
    unusual value (non-string keys, a cycle) cannot stop the run.
    """
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return repr(value)


def _parameter_values(parameters) -> dict[str, list[tuple]]:
    """Each parameter's dated values and metadata, and each node's metadata.

    For a parameter, every entry of its timeline (date and value) and its
    metadata, so a change on any date, or to how it is uprated, shows; for
    the root, every node and every scale, its metadata and, for a scale,
    its bands' names in order, so an added, removed or reordered band
    shows. Values are recorded as text, so a list changed in place is
    caught. A name can occur more than once (``parameters.baseline``
    repeats the tree), so every occurrence is kept, in tree order.
    """
    from policyengine_core.parameters import Parameter, ParameterScale

    values: dict[str, list[tuple]] = {}
    for item in [parameters, *parameters.get_descendants()]:
        if isinstance(item, Parameter):
            values.setdefault(item.name, []).append(
                (
                    tuple(
                        (entry.instant_str, _frozen(entry.value))
                        for entry in item.values_list
                    ),
                    _frozen(item.metadata),
                )
            )
        else:
            bands = (
                tuple(band.name for band in item.brackets)
                if isinstance(item, ParameterScale)
                else None
            )
            values.setdefault(f"{item.name}#node", []).append(
                (_frozen(getattr(item, "metadata", None)), bands)
            )
    return values


def _shared_trees() -> dict:
    """policyengine-uk's shared parameter state that a reform could leak into.

    The module system's parameters, and (where the installed version has
    them) the cached processed tree every new simulation copies, the cached
    statutory tree reforms are written onto, and the cached projected
    timelines. The caches are module globals, read without building them.

    Not watched: policyengine-uk's memo of rebuilt reform trees, which the
    run itself fills, so there is no state from before the run to compare
    it with. A leak into it would show in the reformed values the cases
    check against their oracles.
    """
    import importlib

    from policyengine_uk.system import system

    module = importlib.import_module("policyengine_uk.tax_benefit_system")
    trees = {"system": system.parameters}
    for name, attribute in (
        ("processed", "_processed_parameters_cache"),
        ("statutory", "_statutory_parameters_cache"),
        ("projected", "_projected_timelines_cache"),
    ):
        value = getattr(module, attribute, None)
        if value is not None:
            trees[name] = value
    return trees


def _state_values(tree) -> dict:
    if isinstance(tree, Mapping):
        # Timelines by name: each entry's date and value.
        return {
            name: [
                (entry.instant_str, _frozen(entry.value)) for entry in timeline or []
            ]
            for name, timeline in tree.items()
        }
    return _parameter_values(tree)


def shared_state() -> dict:
    """The values of policyengine-uk's shared parameter state, by tree."""
    return {name: _state_values(tree) for name, tree in _shared_trees().items()}


def module_parameters_unchanged(before: dict) -> dict:
    """A report row: the shared parameter state still equals ``before``.

    ``before`` is :func:`shared_state` taken before any reform ran.
    """
    now = shared_state()
    changed = []
    for tree in sorted(before.keys() | now.keys()):
        if tree not in before:
            # Built during the run, so there is nothing to compare it with.
            continue
        old, new = before[tree], now.get(tree, {})
        changed += [
            f"{tree}:{path}"
            for path in sorted(old.keys() | new.keys())
            if old.get(path) != new.get(path)
        ]
    return {
        "case_id": "module_parameters_unchanged",
        "route": "all",
        "reform_digest": None,
        **RUN_LEVEL_IDENTITY,
        "check": (
            "every parameter's dated values and metadata, and every node's "
            f"metadata and band order, in {', '.join(sorted(before))}"
        ),
        "status": FAIL if changed else PASS,
        "expected": "policyengine-uk's shared parameters as they were before the run",
        "actual": f"{len(changed)} changed: {changed[:10]}" if changed else "unchanged",
        "oracle": "the shared parameter state's values, read before any reform ran",
    }


def _row(case: Case, route: str, digest: Optional[str], **fields) -> dict:
    row = {"case_id": case.id, "route": route, "reform_digest": digest}
    row.update(fields)
    return row


#: The receipt representation (``policyengine.provenance.receipt``,
#: docs/receipts.md) of the reform each route consumes, for its rows'
#: ``reform_identity``. Both wrapper routes hand the wrapper the same
#: ``{parameter: {date key: value}}`` dict: ``calculate_household(reform=...)``
#: takes it, and the policy route compiles it with ``compile_reform_to_policy``.
#: None where receipt schema v1 names no representation for what the route
#: consumes.
ROUTE_REPRESENTATIONS = {
    "country.reform_dict": "policyengine-uk.reform_dict/v1",
    "country.scenario_parameter_changes": "policyengine-uk.scenario/v1",
    "country.reform_from_dict": None,
    "wrapper.household": "policyengine.reform_dict/v1",
    "wrapper.policy": "policyengine.reform_dict/v1",
}


def row_reform_identity(
    case: Case, route: str, representation: Any
) -> tuple[Optional[dict], Optional[str]]:
    """The reform a row ran, as a receipt binds it, or why it cannot be bound.

    ``ReformIdentity.model_dump(mode="json")``, the shape of a receipt's
    ``reform`` field, named by the case id. Digests are never normalized
    across representations, so a route whose input has no representation in
    receipt schema v1 gets None and a reason rather than another route's.
    """
    from policyengine.provenance.receipt import (
        reform_identity,
        scenario_reform_identity,
    )

    if route in UNSUPPORTED_ROUTES:
        return None, "the route does not run in-process"
    if case.modifier:
        return None, (
            "the case's simulation modifier is a closure, which "
            "scenario_reform_identity refuses to bind"
        )
    kind = ROUTE_REPRESENTATIONS.get(route)
    if kind is None:
        return (
            None,
            f"receipt schema v1 has no representation for what {route} consumes",
        )
    try:
        if kind == "policyengine-uk.scenario/v1":
            from policyengine_uk.utils.scenario import Scenario

            identity = scenario_reform_identity(
                Scenario(parameter_changes=representation), name=case.id
            )
        else:
            identity = reform_identity(representation, kind, name=case.id)
    except Exception as error:  # noqa: BLE001 - recorded on the row, never raised
        # ReceiptError for a value receipts refuse; a Scenario's own
        # validation for a change it cannot hold, which the route then
        # reports itself.
        return None, f"{type(error).__name__}: {error}"
    return identity.model_dump(mode="json"), None


def _with_reform_identity(rows: list[dict], identity, unavailable) -> list[dict]:
    for row in rows:
        row["reform_identity"] = identity
        if identity is None:
            row["reform_identity_unavailable"] = unavailable
    return rows


#: The ``reform_identity`` fields of a run-level row, which runs no reform.
RUN_LEVEL_IDENTITY = {
    "reform_identity": None,
    "reform_identity_unavailable": "a run-level row runs no reform",
}
#: The ``reform_identity`` fields of a sampled property's row and of a
#: population check's row, which carry no single reform's identity.
PROPERTY_IDENTITY = {
    "reform_identity": None,
    "reform_identity_unavailable": (
        "a sampled property runs many sampled reforms, so its row binds none"
    ),
}
POPULATION_IDENTITY = {
    "reform_identity": None,
    "reform_identity_unavailable": (
        "population check rows are not bound to a reform identity"
    ),
}


def _close(actual: float, expected: float, tolerance: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= tolerance


def evaluate_case(
    case: Case,
    route: str,
    cache: Optional[dict] = None,
    reference: Optional[Callable[[str, int], float]] = None,
) -> list[dict]:
    """Run one case through one route; one report row per check.

    ``reference`` reads current law's annual parameters for expected values;
    by default, a copy taken now. Each row carries ``reform_digest`` and
    ``reform_identity`` (see :func:`row_reform_identity`).
    """
    representation = None if route in UNSUPPORTED_ROUTES else represent(case, route)
    identity, unavailable = row_reform_identity(case, route, representation)
    # The run uses the very representation the identity binds.
    return _with_reform_identity(
        _evaluate_case(case, route, cache, reference, representation),
        identity,
        unavailable,
    )


def _evaluate_case(
    case: Case,
    route: str,
    cache: Optional[dict],
    reference: Optional[Callable[[str, int], float]],
    representation: Any,
) -> list[dict]:
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
    digest = reform_digest(representation, route, case)
    context = Context(reference or _baseline_parameter_reader())
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
    for assertion_index, check in enumerate(case.checks):
        label = f"{check.target}:{check.name}:{check.year}"
        # Several assertions can read the same value under different oracles.
        # The index identifies each declared assertion even when labels collide.
        assertion_id = f"{label}:{assertion_index}"
        if check.target == "parameter" and route not in COUNTRY_ROUTES:
            rows.append(
                _row(
                    case,
                    route,
                    digest,
                    check=label,
                    assertion_id=assertion_id,
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
                    assertion_id=assertion_id,
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
                    assertion_id=assertion_id,
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
                assertion_id=assertion_id,
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
    for name, year, after, unreformed in run.after:
        rows.append(
            _row(
                case,
                route,
                digest,
                check=f"unreformed_after_reform:{name}:{year}",
                status=PASS if after == unreformed else FAIL,
                expected=unreformed,
                actual=after,
                oracle=(
                    "an unreformed simulation built after the reform equals one "
                    "built before it"
                ),
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
    """The annual value a single change gives, under contract 2.0.0.

    For the personal allowance, prior law is statute: tax years the change
    covers take its value, years to 2030-31 take current law (Finance Act
    2021 s5 fixes them), and every later year is ITA 2007 s57(3) applied to
    the year before. For the other sampled parameters prior law is current
    law's annual value outside the change. Blended parameters are sampled
    only from 2025 on, where current law holds one value through each fiscal
    year, so each day of the year takes the change's value inside the change
    and prior law's outside it.
    """
    blend, _ = SAMPLED_PARAMETERS[change.path]
    stop = change.stop or FLAT_STOP
    if change.path == PERSONAL_ALLOWANCE:
        return _statutory_allowance(change, year, baseline)
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


def _statutory_allowance(
    change: Change, year: int, baseline: Callable[[str, int], float]
) -> float:
    sample = datetime.date(year, 4, 30)
    if change.start <= sample <= (change.stop or FLAT_STOP):
        return float(change.value)
    if year <= LAST_FROZEN_TAX_YEAR:
        return baseline(PERSONAL_ALLOWANCE, year)
    return s57_personal_allowance(
        _statutory_allowance(change, year - 1, baseline),
        baseline(SEPTEMBER_CPI_RISE, year),
    )


def _property_annual_values(
    change: Change,
    routes: Sequence[str],
    cache: dict,
    reference: Callable[[str, int], float],
) -> None:
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
            expected = expected_annual(change, year, reference)
            assert abs(actual - expected) <= 1e-9, (
                f"{route}: {change.path} in {year} is {actual}, expected {expected}"
            )


SAMPLED_OUTPUTS = (
    "income_tax",
    "capital_gains_tax",
    "uc_standard_allowance",
    "universal_credit",
)
SAMPLED_GAINS = 10_000


def _property_routes_agree(
    change: Change,
    income: int,
    routes: Sequence[str],
    cache: dict,
    reference: Callable[[str, int], float],
) -> None:
    household = adult(income, capital_gains=SAMPLED_GAINS)
    case = Case(
        "sampled",
        "sampled",
        (change,),
        household,
        tuple(
            Check("change", name, year, 0.0, "")
            for name in SAMPLED_OUTPUTS
            for year in (2026, 2028, 2031)
        ),
    )
    results = {}
    for route in routes:
        run = _route(route).run(case, represent(case, route), cache)
        results[route] = dict(run.reformed)
        for name, year, value, unreformed in run.isolation + run.after:
            assert value == unreformed, (
                f"{route}: unreformed {name} in {year} is {value} after the "
                f"reform, {unreformed} before it"
            )
    first_route = next(iter(results))
    first = results[first_route]
    for route, values in results.items():
        for key, value in values.items():
            assert abs(value - first[key]) <= 1e-6, (
                f"{key[1]} in {key[2]} is {value} through {route} and "
                f"{first[key]} through {first_route}"
            )


PROPERTIES = {
    "annual_values_match_the_oracle": "Random single changes on the country routes give the annual values of an independent fiscal-year annualisation.",
    "routes_agree_and_baselines_hold": "Random changes give the same household income tax, capital gains tax, Universal Credit standard allowance and award on every in-process route, and leave each route's baseline and later unreformed simulations unchanged.",
}


def _counterexample(change: Optional[Change], income: Optional[int], detail) -> dict:
    return {
        "change": repr(change),
        "income": income,
        "detail": str(detail)[:2000],
    }


def run_property(
    property_id: str,
    routes: Sequence[str],
    seed: int,
    max_examples: int,
    cache: dict,
    reference: Optional[Callable[[str, int], float]] = None,
) -> dict:
    """Sample ``max_examples`` changes and check one property on each.

    A failed check is ``fail`` and any other exception ``error``, under
    Hypothesis or, when it is not installed, a seeded random sampler; both
    report the change and income that broke the property.
    """
    if max_examples <= 0:
        return {
            "property_id": property_id,
            "status": UNSUPPORTED,
            "examples_run": 0,
            "reason": "max_examples is 0, so no examples were requested",
        }
    reference = reference or _baseline_parameter_reader()
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
            _property_annual_values(change, country, cache, reference)

    else:
        if len(in_process) < 2:
            return {
                "property_id": property_id,
                "status": UNSUPPORTED,
                "examples_run": 0,
                "reason": "needs two in-process routes",
            }

        def check(change, income):
            _property_routes_agree(change, income, in_process, cache, reference)

    examples = 0
    current: list = [None, None]

    def example(change, income):
        nonlocal examples
        examples += 1
        current[:] = [change, income]
        check(change, income)
        release_dead_variable_modules()

    try:
        from hypothesis import HealthCheck, Phase, given, settings
        from hypothesis import seed as hypothesis_seed
        from hypothesis import strategies as st
    except ImportError:
        engine = "random"
    else:
        engine = "hypothesis"
    try:
        if engine == "hypothesis":

            @hypothesis_seed(seed)
            @settings(
                max_examples=max_examples,
                deadline=None,
                database=None,
                suppress_health_check=list(HealthCheck),
                # Shrinking reruns a failing example many times; each example
                # builds several simulations, so it is left out to bound
                # runtime. The first failure is reported as found.
                phases=[Phase.explicit, Phase.generate],
                report_multiple_bugs=False,
            )
            @given(
                change=st.randoms(use_true_random=False).map(_sampled_change),
                income=st.integers(0, 150_000),
            )
            def sampled(change, income):
                example(change, income)

            sampled()
        else:
            rng = random.Random(seed)
            for _ in range(max_examples):
                example(_sampled_change(rng), rng.randrange(0, 150_001))
    except AssertionError as failure:
        return {
            "property_id": property_id,
            "engine": engine,
            "examples_run": examples,
            "status": FAIL,
            "counterexample": _counterexample(*current, failure),
        }
    except Exception as error:  # noqa: BLE001 - a crash is a contract error
        return {
            "property_id": property_id,
            "engine": engine,
            "examples_run": examples,
            "status": ERROR,
            "counterexample": _counterexample(
                *current,
                "".join(traceback.format_exception_only(type(error), error)).strip(),
            ),
        }
    return {
        "property_id": property_id,
        "engine": engine,
        "examples_run": examples,
        "status": PASS,
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
    if not selected_routes:
        raise ValueError(f"No routes selected; expected some of {ROUTES}.")
    unknown = [route for route in selected_routes if route not in ROUTES]
    if unknown:
        raise ValueError(f"Unknown routes {unknown}; expected some of {ROUTES}.")
    case_ids = [case.id for case in CASES]
    if cases is not None:
        if not cases:
            raise ValueError("No cases selected; pass None to run every case.")
        unknown = [case_id for case_id in cases if case_id not in case_ids]
        if unknown:
            raise ValueError(f"Unknown cases {unknown}; expected some of {case_ids}.")
    selected_cases = [case for case in CASES if cases is None or case.id in cases]
    # Expected values read current law as it is before any reform runs.
    reference = parameter_reader(reference_parameters())
    before = shared_state()
    cache: dict = {}
    rows: list[dict] = []
    for case in selected_cases:
        for route in selected_routes:
            if case.routes is not None and route not in case.routes:
                continue
            rows.extend(evaluate_case(case, route, cache, reference))
            release_dead_variable_modules()
    properties = [
        run_property(property_id, selected_routes, seed, max_examples, cache, reference)
        for property_id in PROPERTIES
    ]
    population: list[dict] = []
    if dataset_path is not None:
        from policyengine.tax_benefit_models.uk.budget_reform_population import (
            run_population_checks,
        )

        population = run_population_checks(dataset_path, selected_routes, seed)
    for row in properties:
        row.update(PROPERTY_IDENTITY)
    for row in population:
        row.update(POPULATION_IDENTITY)
    # Whether any check passed, before the run-level row (which passes
    # whenever nothing leaked, including when nothing ran).
    passed = any(row["status"] == PASS for row in rows + properties + population)
    if any(route not in UNSUPPORTED_ROUTES for route in selected_routes):
        rows.append(module_parameters_unchanged(before))
    if not passed:
        # A run in which nothing passed certifies nothing.
        rows.append(
            {
                "case_id": "run",
                "route": "all",
                "reform_digest": None,
                **RUN_LEVEL_IDENTITY,
                "check": "at least one check passed",
                "status": ERROR,
                "detail": "no case, property or population check passed",
            }
        )
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
