"""Report rows from ``evaluate_case`` over fixed fake routes.

``test_uk_budget_reform_contract.py`` compares these rows, without their
``assertion_id``, with rows recorded from the runner before assertion ids
existed (``fixtures/uk_contract/evaluate_case_rows.json``), so labelling the
rows cannot change any verdict, expected value or actual value. To record the
fixture again from a given runner:

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

            class Route:
                def run(self, case, representation, cache):
                    if error is not None:
                        raise error
                    run = contract.RouteRun()
                    run.reformed = _Values(reformed)
                    run.unreformed = _Values(unreformed)
                    run.isolation.extend(extra)
                    run.after.extend(extra)
                    return run

            contract._route = lambda name: Route()
            for case in cases:
                for route in contract.ROUTES:
                    for row in contract.evaluate_case(case, route):
                        rows.append(
                            {"variant": variant}
                            | {key: row.get(key) for key in VERDICT_FIELDS}
                        )
    finally:
        contract._route, contract._baseline_parameter_reader = saved
    return json.loads(json.dumps(rows, default=str))


if __name__ == "__main__":
    from policyengine.tax_benefit_models.uk import budget_reform_contract as contract

    rows = scenario_rows(contract, contract.CASES)
    with open(sys.argv[1], "w") as handle:
        json.dump(rows, handle, sort_keys=True)
        handle.write("\n")
    print(len(rows), "rows")
