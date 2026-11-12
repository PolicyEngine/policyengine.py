"""Managed regional calculations retain the native supplied history."""

from __future__ import annotations

import copy
import gc
import importlib
import weakref
from types import SimpleNamespace

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

us_model = importlib.import_module("policyengine.tax_benefit_models.us.model")


def _inject_native_source(monkeypatch, native):
    """Inject synthetic supplied history at the materialization boundary.

    All native constructors, input writes, projections and formulas remain
    real. The test replaces only source resolution and its file provenance.
    """
    monkeypatch.setattr(
        us_model,
        "materialize_dataset",
        lambda *args, **kwargs: SimpleNamespace(
            path=native, source_uri="synthetic://supplied-history", bundle_dataset=None
        ),
    )
    monkeypatch.setattr(
        us_model,
        "build_runtime_dataset_provenance",
        lambda *args: {"source_uri": "synthetic://supplied-history"},
    )


def _managed(**kwargs):
    return us_model.managed_microsimulation(
        dataset="synthetic-history",
        allow_unmanaged=True,
        spm={"geography_kind": "national", "scenario": "zero_real"},
        **kwargs,
    )


def _native(years=(2023, 2025)):
    singles = []
    for year in years:
        person = pd.DataFrame(
            {
                "person_id": [909, 37, 604],
                "age": [66 + year - 2023, 40, 8],
                "is_household_head": [True, True, False],
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
    native.datasets[2023].person["person_tax_unit_id"] = [23, 91, 23]
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


def test_refuses_conflicting_eternity_inputs_and_orphan_groups():
    native = _native()
    native.datasets[2025].person.loc[0, "is_household_head"] = False
    strategy = RowFilterStrategy(variable_name="state_fips", variable_value=41)
    with pytest.raises(ValueError, match="Conflicting ETERNITY"):
        scope_native_history(
            native,
            strategy,
            {"is_household_head": SimpleNamespace(definition_period="eternity")},
        )
    native = _native()
    native.datasets[2023].family.loc[2] = [999]
    with pytest.raises(ValueError, match="members in every family"):
        scope_native_history(native, strategy)


def test_unsupported_strategy_and_legacy_spm_fail_before_country_construction(
    monkeypatch,
):
    import policyengine_us

    from policyengine.core.scoping_strategy import RegionGroupStrategy

    _inject_native_source(monkeypatch, _native())

    def forbidden_constructor(*args, **kwargs):
        pytest.fail("unsupported scope reached native construction")

    monkeypatch.setattr(policyengine_us, "Microsimulation", forbidden_constructor)
    strategy = RowFilterStrategy(variable_name="state_fips", variable_value=41)
    with pytest.raises(ValueError, match="only RowFilterStrategy"):
        _managed(scoping_strategy=RegionGroupStrategy(members=[strategy]))
    monkeypatch.setattr(us_model, "legacy_spm_source", lambda *args: object())
    with pytest.raises(ValueError, match="legacy SPM"):
        _managed(scoping_strategy=strategy)


@pytest.mark.parametrize("reform", [False, True])
def test_real_managed_scope_keeps_all_supplied_inputs_and_releases_source(
    monkeypatch, reform
):
    """Country input holders, live IDs and native weights retain the history."""
    import policyengine_us

    native = _native()
    _inject_native_source(monkeypatch, native)
    constructor = policyengine_us.Microsimulation
    if reform:
        from policyengine_core.reforms import Reform

        policy = Reform.from_dict(
            {
                "gov.irs.deductions.standard.amount.SINGLE": {
                    "2025-01-01.2100-12-31": 100_000
                }
            },
            country_id="us",
        )
    else:
        policy = None
    unscoped = _managed(reform=policy)
    constructed = []

    def observed_constructor(*args, **kwargs):
        if constructed:
            gc.collect()
            assert constructed[0]() is None, "national input simulation remained live"
            assert kwargs["dataset"].datasets[2023].household.household_id.tolist() == [
                91
            ]
        result = constructor(*args, **kwargs)
        constructed.append(weakref.ref(result))
        return result

    monkeypatch.setattr(policyengine_us, "Microsimulation", observed_constructor)
    scoped = _managed(
        reform=policy,
        scoping_strategy=RowFilterStrategy(
            variable_name="state_fips", variable_value=41
        ),
    )
    assert len(constructed) == 2
    assert scoped.is_over_dataset
    assert scoped.default_calculation_period == "2023"
    assert scoped.dataset.years == [2023, 2025]
    assert scoped.policyengine_bundle["source_uri"] == "synthetic://supplied-history"
    assert scoped.policyengine_bundle["legacy_input_renames"] == {
        "would_claim_wic": "takes_up_wic_if_eligible"
    }
    source_arms = [unscoped, unscoped.baseline] if reform else [unscoped]
    scoped_arms = [scoped, scoped.baseline] if reform else [scoped]
    for source_arm, scoped_arm in zip(source_arms, scoped_arms):
        for name in source_arm.input_variables:
            entity = source_arm.tax_benefit_system.variables[name].entity.key
            source_ids = np.asarray(source_arm.populations[entity].ids)
            target_ids = np.asarray(scoped_arm.populations[entity].ids)
            positions = pd.Index(source_ids).get_indexer(target_ids)
            assert (positions >= 0).all()
            holder = source_arm.get_holder(name)
            supplied = holder.get_input_periods(source_arm.branch_name)
            assert {str(p) for p in supplied} == {
                str(p)
                for p in scoped_arm.get_holder(name).get_input_periods(
                    scoped_arm.branch_name
                )
            }, name
            for period in supplied:
                np.testing.assert_array_equal(
                    scoped_arm.get_array(name, period),
                    source_arm.get_array(name, period)[positions],
                    err_msg=f"{name}/{period}",
                )
        if reform:
            assert (
                scoped_arm.tax_benefit_system.parameters(
                    "2025-01-01"
                ).gov.irs.deductions.standard.amount.SINGLE
                == source_arm.tax_benefit_system.parameters(
                    "2025-01-01"
                ).gov.irs.deductions.standard.amount.SINGLE
            )
        expected_tax = source_arm.calculate("income_tax", 2025, map_to="household")
        actual_tax = scoped_arm.calculate("income_tax", 2025, map_to="household")
        assert actual_tax.tolist() == [expected_tax.iloc[1]]
        assert actual_tax.weights.tolist() == [7.25]
    if reform:
        assert (
            scoped.calculate("income_tax", 2025).tolist()
            != scoped.baseline.calculate("income_tax", 2025).tolist()
        )
    for year in (2023, 2025):
        assert scoped.calculate("person_id", year).tolist() == [909]
        for group in GROUPS:
            assert scoped.calculate(f"{group}_id", year).tolist() == [91]
            assert scoped.calculate(f"person_{group}_id", year).tolist() == [91]
        for month in range(1, 13):
            period = f"{year}-{month:02d}"
            holder = scoped.get_holder("takes_up_wic_if_eligible")
            assert period in {
                str(p) for p in holder.get_input_periods(scoped.branch_name)
            }
            assert scoped.calculate("takes_up_wic_if_eligible", period).tolist() == [
                False
            ]
        income = scoped.calculate("employment_income", year, map_to="household")
        assert income.weights.tolist() == [7.25]
        assert income.tolist() == [50_000 if year == 2023 else 300_000]


def test_real_history_scope_preserves_irmaa_and_snap_medical_deduction(monkeypatch):
    """Earlier income changes an actual Medicare premium and SNAP deduction."""
    native = _native()
    _inject_native_source(monkeypatch, native)
    unscoped = _managed()
    if (
        "medicare_irmaa_magi_two_years_prior"
        not in unscoped.tax_benefit_system.variables
    ):
        pytest.skip("This country pin predates the Medicare IRMAA lookback variable")
    from policyengine_us.tools.general import earliest_input_year

    scoped = _managed(
        scoping_strategy=RowFilterStrategy(
            variable_name="state_fips", variable_value=41
        )
    )
    _inject_native_source(monkeypatch, _native(years=(2025,)))
    target_only = _managed(
        scoping_strategy=RowFilterStrategy(
            variable_name="state_fips", variable_value=41
        )
    )
    assert earliest_input_year(scoped) == 2023
    assert earliest_input_year(target_only) == 2025
    assert scoped.calculate("medicare_irmaa_magi_two_years_prior", 2025)[
        0
    ] == pytest.approx(50_000)
    assert (
        target_only.calculate("medicare_irmaa_magi_two_years_prior", 2025)[0] > 200_000
    )
    for variable in (
        "medicare_irmaa_magi_two_years_prior",
        "gross_medicare_part_b_premium",
        "medicare_part_b_premium",
        "snap_allowable_medical_expenses",
    ):
        expected = unscoped.calculate(variable, 2025, map_to="household")
        actual = scoped.calculate(variable, 2025, map_to="household")
        # The source household table deliberately puts the selected ID second.
        assert actual.tolist() == [expected.iloc[1]]
        assert actual.weights.tolist() == [7.25]
    base = scoped.calculate("base_part_b_premium", 2025)[0]
    assert scoped.calculate("gross_medicare_part_b_premium", 2025)[0] == base
    assert target_only.calculate("gross_medicare_part_b_premium", 2025)[0] > base
    assert (
        target_only.calculate("snap_allowable_medical_expenses", 2025)[0]
        > scoped.calculate("snap_allowable_medical_expenses", 2025)[0]
        > 0
    )
