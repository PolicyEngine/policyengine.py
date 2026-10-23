"""Report rows from ``evaluate_case`` over fixed fake routes.

``test_uk_budget_reform_contract.py`` compares these rows, without their
``assertion_id``, with recorded rows
(``fixtures/uk_contract/evaluate_case_rows.json``), so labelling the rows cannot
change any verdict, expected value or actual value. The rows were recorded
from main's runner at ``503d4998`` and recorded again for contract 2.0.0
(cos d1344), whose only row changes are the extended freeze's checks after
2033-34. The real cases exercise
fixed fake routes; focused cases cover matching comparisons, tolerances,
missing values, matching pending checks and expected rejections. To record
the fixture again, put a source tree holding main's runner first on
``PYTHONPATH`` and run:

    python tests/uk_contract_row_scenarios.py tests/fixtures/uk_contract/evaluate_case_rows.json
"""

import hashlib
import json
import sys


class _Values(dict):
    """A route's values: any requested key gets a fixed, key-specific value."""

    def __init__(self, value):
        super().__init__()
        self._value = value

    def __missing__(self, key):
        return self._value(key)


def _hashed(key, salt: str) -> float:
    digest = hashlib.sha256(repr((salt, *key)).encode()).digest()
    return round(int.from_bytes(digest[:4], "big") / 2**32 * 1000, 6)


def _flat(key) -> float:
    return 0.20 if key[0] == "parameter" else 1000.0


#: The row fields that make up a verdict: which check, its status, and the
#: values compared.
VERDICT_FIELDS = (
    "case_id",
    "route",
    "check",
    "status",
    "expected",
    "actual",
    "decision_id",
    "holds",
)

#: name: (reformed values, unreformed values, isolation and after rows, error)
VARIANTS = {
    "hashed": (
        lambda key: _hashed(key, "reformed"),
        lambda key: _hashed(key, "unreformed"),
        [("income_tax", 2027, 5.0, 5.0), ("income_tax", 2028, 5.0, 6.0)],
        None,
    ),
    "unchanged": (_flat, _flat, [], None),
    "error": (None, None, [], RuntimeError("route failed")),
}


def scenario_rows(contract, cases) -> list[dict]:
    """Rows for every case, route and variant, without assertion ids."""

    saved = contract._route, contract._baseline_parameter_reader
    rows = []
    try:
        contract._baseline_parameter_reader = lambda: lambda path, year: 0.20
        for variant, (reformed, unreformed, extra, error) in VARIANTS.items():
            for case in cases:
                rows.extend(
                    _case_rows(
                        contract,
                        variant,
                        case,
                        _Values(reformed),
                        _Values(unreformed),
                        extra,
                        error,
                    )
                )
        for variant, case, reformed, unreformed, error in _focused_scenarios(contract):
            rows.extend(
                _case_rows(contract, variant, case, reformed, unreformed, (), error)
            )
    finally:
        contract._route, contract._baseline_parameter_reader = saved
    return json.loads(json.dumps(rows, default=str))


def _case_rows(contract, variant, case, reformed, unreformed, extra, error):
    class Route:
        def run(self, case, representation, cache):
            if error is not None:
                raise error
            run = contract.RouteRun()
            run.reformed = reformed
            run.unreformed = unreformed
            run.isolation.extend(extra)
            run.after.extend(extra)
            return run

    contract._route = lambda name: Route()
    for route in contract.ROUTES:
        for row in contract.evaluate_case(case, route):
            yield {"variant": variant} | {key: row.get(key) for key in VERDICT_FIELDS}


def _focused_scenarios(contract):
    """Fixed inputs that reach verdict branches missed by the real cases."""

    def case(name, checks=(), expect_error=None):
        return contract.Case(
            id=name,
            title=name,
            changes=(
                contract.Change(
                    contract.BASIC_RATE, contract._date("2027-04-06"), 0.21
                ),
            ),
            household=contract.adult(),
            checks=checks,
            expect_error=expect_error,
        )

    key = ("variable", "income_tax", 2027)
    yield (
        "matching_variable",
        case(
            "matching_variable",
            (
                contract.Check("variable", "income_tax", 2027, 1000.0, "fixed value"),
                contract.Check("change", "income_tax", 2027, 0.0, "unchanged value"),
                contract.Check(
                    "baseline_equals", "income_tax", 2027, "income_tax", "equal values"
                ),
            ),
        ),
        {key: 1000.0},
        {key: 1000.0},
        None,
    )
    yield (
        "tolerance_boundary",
        case(
            "tolerance_boundary",
            (
                contract.Check("variable", "inside", 2027, 174.30, "inside", 0.005),
                contract.Check("variable", "outside", 2027, 174.30, "outside", 0.005),
            ),
        ),
        {
            ("variable", "inside", 2027): 174.303,
            ("variable", "outside", 2027): 174.306,
        },
        {},
        None,
    )
    yield (
        "missing_value",
        case(
            "missing_value",
            (contract.Check("variable", "income_tax", 2027, 1000.0, "missing value"),),
        ),
        {},
        {},
        None,
    )
    yield (
        "matching_pending",
        case(
            "matching_pending",
            (
                contract.Check(
                    "variable",
                    "income_tax",
                    2027,
                    1000.0,
                    "fixed value",
                    pending=contract.PRIOR_LAW_DECISION,
                ),
            ),
        ),
        {key: 1000.0},
        {},
        None,
    )
    yield (
        "matching_rejection",
        case("matching_rejection", expect_error="new_credit"),
        {},
        {},
        ValueError("no new_credit here"),
    )


if __name__ == "__main__":
    from policyengine.tax_benefit_models.uk import budget_reform_contract as contract

    rows = scenario_rows(contract, contract.CASES)
    with open(sys.argv[1], "w") as handle:
        json.dump(rows, handle, sort_keys=True)
        handle.write("\n")
    print(len(rows), "rows")
