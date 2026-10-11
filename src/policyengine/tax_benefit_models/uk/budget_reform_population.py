"""Population checks for the UK Budget reform contract.

Run by :func:`~policyengine.tax_benefit_models.uk.budget_reform_contract.run_budget_reform_contract`
when it is given a certified dataset. They use a deterministic subsample of
the dataset's households, so a data-dependent failure (a reform reaching
the baseline through a cached value, or a route that diverges only for some
households) shows up without the cost of the full population.

Checks:

``population_baseline_isolation``
    An unreformed microsimulation, the ``baseline`` of a reformed one and an
    unreformed one built after the reform give identical arrays.
``population_query_order``
    Calculating the outputs in reverse order gives identical arrays.
``population_routes_agree``
    A basic rate of 21% from 6 April 2027 gives identical income tax arrays
    through the reform dict, ``parameter_changes`` and ``Reform.from_dict``.
``population_april_rate_change``
    That reform leaves 2026 income tax unchanged for every person and never
    lowers anyone's income tax in 2027.
``population_finite_change_expires``
    The same rate for 2027-28 only leaves 2028 identical to the baseline.
"""

from __future__ import annotations

import os
import tempfile
import traceback
from collections.abc import Sequence
from typing import Any

import numpy as np

SUBSAMPLE_HOUSEHOLDS = 1_000
OUTPUTS = ("income_tax", "universal_credit", "household_net_income")
YEARS = (2026, 2027, 2028)
BASIC_RATE = "gov.hmrc.income_tax.rates.uk[0].rate"
APRIL = {BASIC_RATE: {"2027-04-06.2100-12-31": 0.21}}
FINITE = {BASIC_RATE: {"2027-04-06.2028-04-05": 0.21}}


def _filter_year(single_year, households: np.ndarray):
    from policyengine_uk.data import UKSingleYearDataset

    person = single_year.person
    benunit = single_year.benunit
    household = single_year.household
    keep_people = person["person_household_id"].isin(households)
    kept_benunits = person.loc[keep_people, "person_benunit_id"].unique()
    return UKSingleYearDataset(
        person=person[keep_people].reset_index(drop=True),
        benunit=benunit[benunit["benunit_id"].isin(kept_benunits)].reset_index(
            drop=True
        ),
        household=household[household["household_id"].isin(households)].reset_index(
            drop=True
        ),
        fiscal_year=int(str(single_year.time_period)[:4]),
    )


def _h5_path(dataset_path: str, directory: str) -> str:
    """The file under a name ending in .h5, which policyengine-uk requires.

    A content-addressed cache stores the certified file without an
    extension, so link it under one.
    """
    if dataset_path.endswith(".h5"):
        return dataset_path
    linked = os.path.join(directory, "dataset.h5")
    os.symlink(os.path.abspath(dataset_path), linked)
    return linked


def subsample(dataset_path: str, households: int, seed: int):
    """A deterministic subsample of a policyengine-uk dataset file."""
    with tempfile.TemporaryDirectory() as directory:
        return _subsample(_h5_path(dataset_path, directory), households, seed)


def _subsample(dataset_path: str, households: int, seed: int):
    from policyengine_uk.data import UKMultiYearDataset, UKSingleYearDataset

    if UKMultiYearDataset.validate_file_path(dataset_path, False):
        dataset = UKMultiYearDataset(dataset_path)
        first = dataset[dataset.years[0]]
    else:
        dataset = UKSingleYearDataset(dataset_path)
        first = dataset
    ids = np.sort(first.household["household_id"].to_numpy())
    rng = np.random.default_rng(seed)
    chosen = np.sort(rng.choice(ids, size=min(households, len(ids)), replace=False))
    if isinstance(dataset, UKMultiYearDataset):
        return UKMultiYearDataset(
            datasets=[_filter_year(dataset[year], chosen) for year in dataset.years]
        )
    return _filter_year(dataset, chosen)


def _arrays(simulation, order: int = 1) -> dict[str, np.ndarray]:
    pairs = [(variable, year) for variable in OUTPUTS for year in YEARS][::order]
    return {
        f"{variable}:{year}": np.asarray(
            simulation.calculate(variable, year), dtype=float
        )
        for variable, year in pairs
    }


def _same(a: dict[str, np.ndarray], b: dict[str, np.ndarray]) -> list[str]:
    return [key for key in a if not np.array_equal(a[key], b[key], equal_nan=True)]


def _row(check_id: str, route: str, status: str, **fields: Any) -> dict:
    return {"check_id": check_id, "route": route, "status": status, **fields}


def run_population_checks(
    dataset_path: str, routes: Sequence[str], seed: int = 0
) -> list[dict]:
    """Run the population checks; one report row per check."""
    from policyengine_core.reforms import Reform
    from policyengine_uk import Microsimulation
    from policyengine_uk.utils.scenario import Scenario

    country = [route for route in routes if route.startswith("country.")]
    if not country:
        return [
            _row(
                "population",
                "-",
                "unsupported",
                reason="population checks need a country route",
            )
        ]
    rows: list[dict] = []
    try:
        data = subsample(dataset_path, SUBSAMPLE_HOUSEHOLDS, seed)

        def build(route: str | None, reform: dict | None):
            if reform is None:
                return Microsimulation(dataset=data.copy())
            if route == "country.reform_dict":
                return Microsimulation(dataset=data.copy(), reform=reform)
            if route == "country.scenario_parameter_changes":
                return Microsimulation(
                    dataset=data.copy(), scenario=Scenario(parameter_changes=reform)
                )
            return Microsimulation(
                dataset=data.copy(),
                reform=Reform.from_dict(reform, country_id="uk"),
            )

        before = _arrays(build(None, None))
        reformed = {route: build(route, APRIL) for route in country}
        for route, simulation in reformed.items():
            different = _same(before, _arrays(simulation.baseline))
            rows.append(
                _row(
                    "population_baseline_isolation",
                    route,
                    "fail" if different else "pass",
                    detail=different or None,
                )
            )
        after = _arrays(build(None, None))
        different = _same(before, after)
        rows.append(
            _row(
                "population_baseline_isolation",
                "unreformed",
                "fail" if different else "pass",
                detail=different or None,
            )
        )
        different = _same(before, _arrays(build(None, None), order=-1))
        rows.append(
            _row(
                "population_query_order",
                "unreformed",
                "fail" if different else "pass",
                detail=different or None,
            )
        )
        tax = {
            route: {
                year: np.asarray(simulation.calculate("income_tax", year), dtype=float)
                for year in (2026, 2027)
            }
            for route, simulation in reformed.items()
        }
        first = country[0]
        for route in country[1:]:
            same = all(
                np.array_equal(tax[route][year], tax[first][year])
                for year in (2026, 2027)
            )
            rows.append(
                _row(
                    "population_routes_agree",
                    f"{first} = {route}",
                    "pass" if same else "fail",
                )
            )
        for route in country:
            unchanged_2026 = np.array_equal(tax[route][2026], before["income_tax:2026"])
            change_2027 = tax[route][2027] - before["income_tax:2027"]
            ok = unchanged_2026 and bool(np.all(change_2027 >= -1e-6))
            rows.append(
                _row(
                    "population_april_rate_change",
                    route,
                    "pass" if ok else "fail",
                    detail={
                        "2026_unchanged": unchanged_2026,
                        "2027_people_with_lower_tax": int(np.sum(change_2027 < -1e-6)),
                        "2027_people_with_higher_tax": int(np.sum(change_2027 > 1e-6)),
                    },
                )
            )
        for route in country:
            simulation = build(route, FINITE)
            same = np.array_equal(
                np.asarray(simulation.calculate("income_tax", 2028), dtype=float),
                before["income_tax:2028"],
            )
            rows.append(
                _row(
                    "population_finite_change_expires",
                    route,
                    "pass" if same else "fail",
                )
            )
    except Exception as error:  # noqa: BLE001 - reported, never swallowed
        rows.append(
            _row(
                "population",
                "-",
                "error",
                detail="".join(
                    traceback.format_exception_only(type(error), error)
                ).strip()[:1000],
            )
        )
    for row in rows:
        row.setdefault("subsample_households", SUBSAMPLE_HOUSEHOLDS)
        row.setdefault("seed", seed)
    return rows
