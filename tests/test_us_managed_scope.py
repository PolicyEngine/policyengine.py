"""Managed regional calculations retain the native supplied history."""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("policyengine_us")
from policyengine_us.data import USMultiYearDataset, USSingleYearDataset  # noqa: E402

from policyengine.core.scoping_strategy import RowFilterStrategy  # noqa: E402
from policyengine.tax_benefit_models.us.managed_scope import (  # noqa: E402
    ENTITIES,
    GROUPS,
    scope_native_history,
)


def _native(years=(2023, 2025)):
    singles = []
    for year in years:
        person = pd.DataFrame(
            {
                "person_id": [909, 37, 604],
                "age": [66 + year - 2023, 40, 8],
                "employment_income": [50_000 if year == 2023 else 300_000, 10_000, 0],
                "would_claim_wic": [False, True, False],
                **{f"person_{group}_id": [91, 23, 23] for group in GROUPS},
            }
        )
        tables = {"person": person}
        for group in GROUPS:
            tables[group] = pd.DataFrame({f"{group}_id": [23, 91]})
        tables["household"]["state_fips"] = [6, 41]
        tables["household"]["household_weight"] = [13.5, 7.25]
        singles.append(USSingleYearDataset(**tables, time_period=year))
    return USMultiYearDataset(datasets=singles)


def test_scopes_all_years_and_retains_native_values_order_and_weights():
    native = _native()
    original = copy.deepcopy(native)
    scoped, receipt = scope_native_history(
        native, RowFilterStrategy(variable_name="state_fips", variable_value=41)
    )
    assert scoped.years == [2023, 2025]
    assert scoped.time_period == native.time_period == "2023"
    assert receipt["years"]["2023"]["scoped_rows"]["household"] == 1
    for year in native.years:
        for entity in ENTITIES:
            pd.testing.assert_frame_equal(
                getattr(native.datasets[year], entity),
                getattr(original.datasets[year], entity),
            )
            expected = getattr(native.datasets[year], entity)
            own_id = f"{entity}_id"
            expected = expected[expected[own_id] == (909 if entity == "person" else 91)]
            pd.testing.assert_frame_equal(
                getattr(scoped.datasets[year], entity), expected.reset_index(drop=True)
            )
    assert scoped.datasets[2023].person.employment_income.tolist() == [50_000]
    assert scoped.datasets[2025].person.employment_income.tolist() == [300_000]
    assert scoped.datasets[2025].household.household_weight.tolist() == [7.25]


def test_refuses_cohort_change_and_cross_household_groups():
    native = _native()
    native.datasets[2025].household["state_fips"] = [41, 6]
    strategy = RowFilterStrategy(variable_name="state_fips", variable_value=41)
    with pytest.raises(ValueError, match="same ordered cohort"):
        scope_native_history(native, strategy)
    native = _native()
    native.datasets[2023].person["person_tax_unit_id"] = [23, 23, 23]
    with pytest.raises(ValueError, match="household-closed"):
        scope_native_history(native, strategy)


@pytest.mark.parametrize("defect", ["duplicate_id", "dangling", "duplicate_column"])
def test_refuses_invalid_native_relationships(defect):
    native = _native()
    if defect == "duplicate_id":
        native.datasets[2023].person["person_id"] = [909, 909, 604]
    elif defect == "dangling":
        native.datasets[2023].person["person_family_id"] = [999, 23, 23]
    else:
        frame = native.datasets[2023].person
        native.datasets[2023].person = pd.concat([frame, frame[["age"]]], axis=1)
    with pytest.raises(ValueError):
        scope_native_history(
            native, RowFilterStrategy(variable_name="state_fips", variable_value=41)
        )


def test_scoped_tables_do_not_share_source_buffers():
    native = _native()
    scoped, _ = scope_native_history(
        native, RowFilterStrategy(variable_name="state_fips", variable_value=41)
    )
    for year in scoped.years:
        for entity in ENTITIES:
            for name in getattr(scoped.datasets[year], entity):
                assert not np.shares_memory(
                    getattr(scoped.datasets[year], entity)[name].to_numpy(),
                    getattr(native.datasets[year], entity)[name].to_numpy(),
                )
