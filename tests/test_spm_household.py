"""Real household acceptance for the canonical SPM measurement contract.

Development runs use the explicit local-wheel manifest pytest plugin; these
tests never replace the packaged production manifest or claim certification.
"""

import json
import math
from copy import deepcopy

import numpy as np
import pytest

# The canonical calculator API is not published yet. Skip rather than weaken
# these cases: they must run against the real module, never a substitute.
pytest.importorskip("spm_calculator.errors")
pytest.importorskip("spm_calculator.release")
pytest.importorskip("spm_calculator.rolling_forecast")
pytest.importorskip("spm_calculator.policyengine_adapter")

from spm_calculator.errors import SPMInputError  # noqa: E402
from spm_calculator.release import SPMUnit  # noqa: E402
from spm_calculator.rolling_forecast import load_forecast  # noqa: E402

import policyengine as pe
from policyengine.tax_benefit_models.us.spm import resolve_spm_selection

AMOUNT_VARIABLES = {
    "spm_unit_reference_spm_threshold": "reference_threshold",
    "spm_unit_unadjusted_spm_threshold": "unadjusted_threshold",
    "spm_unit_geographic_adjustment": "geographic_factor",
    "spm_unit_spm_threshold": "threshold",
    "spm_unit_spm_threshold_housing_portion": "housing_portion",
}

# Spell out the public boundary independently of the adapter's validation set
# so accidentally removing an owned output cannot also remove its test case.
FORMULA_OWNED_VARIABLES = [
    *AMOUNT_VARIABLES,
    "spm_measurement_adults",
    "spm_measurement_children",
    "spm_unit_capped_housing_subsidy",
    "spm_unit_net_income",
    "spm_unit_benefits",
    "spm_unit_is_in_spm_poverty",
    "spm_unit_is_in_deep_spm_poverty",
    "poverty_line",
    "poverty_gap",
]


def household_inputs(**overrides):
    """One adult with observed location, tenure and earnings, no baked outputs."""
    values = {
        "people": [{"age": 40, "employment_income": 50_000}],
        "tax_unit": {"filing_status": "SINGLE"},
        "spm_unit": {"spm_unit_tenure_type": "RENTER"},
        "household": {"state_code": "CA", "county_fips": "06037"},
        "year": 2026,
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize("year", [2024, 2026, 2035])
def test_explicit_national_amounts_and_component_provenance(year, tmp_path):
    result = pe.us.calculate_household(
        **household_inputs(year=year),
        spm={"geography_kind": "national"},
        extra_variables=list(AMOUNT_VARIABLES),
    )
    forecast = load_forecast()
    expected = forecast.calculate_unit(
        SPMUnit(
            unit_id="wrapper-acceptance",
            year=year,
            num_adults=1,
            num_children=0,
            tenure="renter",
            geography_kind="national",
        ),
        scenario=resolve_spm_selection()["scenario"],
    )
    # Each exported amount is the canonical final value cast once to the
    # country's float32 storage, rather than recombined stored intermediates.
    for variable, field in AMOUNT_VARIABLES.items():
        assert result.spm_unit[variable] == float(np.float32(expected[field]))
    assert math.isfinite(result.household.household_net_income)
    assert result.to_dict()["provenance"]["spm_config"] == resolve_spm_selection(
        {"geography_kind": "national"}
    )
    receipt = result.to_dict()["provenance"]["spm"]
    assert (
        receipt["forecast_sha256"] == resolve_spm_selection()["forecast_content_sha256"]
    )
    assert receipt["geography_kind"] == "national"
    assert receipt["years"][str(year)] == forecast.entry(
        year, scenario=receipt["scenario"]
    )
    assert receipt["geographies"]
    assert all(item["county_assignment"] is None for item in receipt["geographies"])
    assert receipt["runtime_versions"]["spm-calculator"]
    assert json.loads(json.dumps(result.to_dict())) == result.to_dict()
    path = result.write(tmp_path / f"household-{year}.json")
    assert json.loads(path.read_text())["provenance"]["spm"] == receipt


def test_default_county_and_explicit_metro_resolve_the_same_area():
    inputs = household_inputs()
    county = pe.us.calculate_household(**inputs, extra_variables=list(AMOUNT_VARIABLES))
    receipt = county.to_dict()["provenance"]["spm"]
    assignment = receipt["geographies"][0]["county_assignment"]
    expected_assignment = load_forecast().resolve_county(
        2026, "06037", county_vintage="2020", scenario=receipt["scenario"]
    )
    assert assignment == expected_assignment
    assert receipt["geography_kind"] == "county"
    metro = pe.us.calculate_household(
        **inputs,
        spm={"geography_kind": "metro", "geography_id": assignment["area_id"]},
        extra_variables=list(AMOUNT_VARIABLES),
    )
    for variable in AMOUNT_VARIABLES:
        assert county.spm_unit[variable] == metro.spm_unit[variable]
    assert inputs == household_inputs()


@pytest.mark.parametrize(
    "location,settings,code",
    [
        ({"state_code": "CA"}, {}, "SPM_GEOGRAPHY_REQUIRED"),
        (
            {"state_code": "CA", "county_fips": "99999"},
            {},
            "SPM_GEOGRAPHY_UNAVAILABLE",
        ),
        (
            {"state_code": "CA"},
            {"geography_kind": "metro", "geography_id": "unavailable-area"},
            "SPM_GEOGRAPHY_UNAVAILABLE",
        ),
    ],
)
def test_default_resource_outputs_require_a_real_geography(location, settings, code):
    with pytest.raises(SPMInputError) as caught:
        pe.us.calculate_household(**household_inputs(household=location), spm=settings)
    assert caught.value.code == code
    assert caught.value.to_dict()["code"] == code


def test_state_only_tax_graph_succeeds_and_resource_graph_requires_geography(
    monkeypatch,
):
    from policyengine.tax_benefit_models.us.model import us_latest

    # Limit only this test's requested outputs. The public wrapper continues to
    # include resources and SPM poverty by default.
    monkeypatch.setattr(us_latest, "entity_variables", {"tax_unit": ["income_tax"]})
    inputs = household_inputs(household={"state_code": "CA"})
    tax = pe.us.calculate_household(**inputs, extra_variables=["housing_assistance"])
    assert tax.tax_unit.income_tax > 0
    assert tax.spm_unit.housing_assistance == 0
    assert tax.to_dict()["provenance"]["spm"]["years"] == {}
    for variable in (
        "household_net_income",
        "household_benefits",
        "marginal_tax_rate",
        "household_income_decile",
        "equiv_household_net_income",
    ):
        with pytest.raises(SPMInputError) as caught:
            pe.us.calculate_household(**inputs, extra_variables=[variable])
        assert caught.value.code == "SPM_GEOGRAPHY_REQUIRED"
    for settings, located_inputs in (
        ({"geography_kind": "national"}, inputs),
        ({"geography_kind": "county"}, household_inputs()),
    ):
        located = pe.us.calculate_household(
            **located_inputs,
            spm=settings,
            extra_variables=["household_net_income", "marginal_tax_rate"],
        )
        assert math.isfinite(located.household.household_net_income)
        assert math.isfinite(located.person[0].marginal_tax_rate)


def test_adultless_measurement_has_a_structured_composition_error():
    with pytest.raises(SPMInputError) as caught:
        pe.us.calculate_household(**household_inputs(people=[{"age": 8}]))
    assert caught.value.code == "SPM_COMPOSITION_REQUIRED"
    assert caught.value.to_dict()["code"] == "SPM_COMPOSITION_REQUIRED"


@pytest.mark.parametrize("variable", sorted(FORMULA_OWNED_VARIABLES))
def test_formula_owned_household_inputs_are_rejected(variable):
    with pytest.raises(ValueError, match="computed outputs supplied as inputs"):
        pe.us.calculate_household(
            **household_inputs(spm_unit={variable: 1}),
        )


@pytest.mark.parametrize("variable", sorted(FORMULA_OWNED_VARIABLES))
def test_formula_owned_axes_are_rejected(variable):
    with pytest.raises(ValueError, match="computed outputs supplied as inputs"):
        pe.us.calculate_household(
            **household_inputs(),
            axes=[{"name": variable, "min": 0, "max": 1, "count": 2}],
        )


@pytest.mark.parametrize(
    "adult",
    [
        {"age": 40, "is_adult": False},
        {"age": 16, "is_adult": False, "is_spm_independent_minor_role": True},
    ],
)
def test_generic_adult_inputs_do_not_override_measurement_counts(adult):
    result = pe.us.calculate_household(
        **household_inputs(
            people=[adult, {"age": 8}],
            spm_unit={"spm_unit_count_adults": 7, "spm_unit_count_children": 9},
        ),
        extra_variables=[
            "spm_unit_count_adults",
            "spm_unit_count_children",
            "spm_measurement_adults",
            "spm_measurement_children",
        ],
    )
    assert result.person[0].is_adult == 0
    assert result.spm_unit.spm_unit_count_adults == 7
    assert result.spm_unit.spm_unit_count_children == 9
    assert result.spm_unit.spm_measurement_adults == 1
    assert result.spm_unit.spm_measurement_children == 1


def test_axes_reforms_and_scenarios_keep_detached_receipts():
    inputs = household_inputs()
    selection = {"geography_kind": "national", "scenario": "ce_trend"}
    baseline = pe.us.calculate_household(
        **inputs, spm=selection, extra_variables=["spm_unit_spm_threshold"]
    )
    baseline_receipt = deepcopy(baseline.to_dict()["provenance"]["spm"])
    axes = pe.us.calculate_household(
        **inputs,
        spm=selection,
        axes=[{"name": "employment_income", "min": 40_000, "max": 60_000, "count": 3}],
        extra_variables=["spm_unit_spm_threshold"],
    )
    assert axes.person[0].employment_income == [40_000, 50_000, 60_000]
    assert (
        axes.spm_unit.spm_unit_spm_threshold
        == [baseline.spm_unit.spm_unit_spm_threshold] * 3
    )
    assert (
        axes.household.household_net_income[1]
        == baseline.household.household_net_income
    )
    reform = pe.us.calculate_household(
        **inputs,
        spm=selection,
        reform={"gov.irs.deductions.standard.amount.SINGLE": 5_000},
        extra_variables=["spm_unit_spm_threshold"],
    )
    assert reform.tax_unit.income_tax > baseline.tax_unit.income_tax
    assert (
        reform.spm_unit.spm_unit_spm_threshold
        == baseline.spm_unit.spm_unit_spm_threshold
    )
    sensitivity = pe.us.calculate_household(
        **inputs,
        spm={"geography_kind": "national", "scenario": "zero_real"},
        extra_variables=["spm_unit_spm_threshold"],
    )
    assert (
        sensitivity.spm_unit.spm_unit_spm_threshold
        != baseline.spm_unit.spm_unit_spm_threshold
    )
    assert baseline.to_dict()["provenance"]["spm"] == baseline_receipt
    exported = baseline.to_dict()
    exported["provenance"]["spm"]["years"].clear()
    assert baseline.to_dict()["provenance"]["spm"] == baseline_receipt
    assert selection == {"geography_kind": "national", "scenario": "ce_trend"}


@pytest.mark.parametrize("year", [2021, 2036])
def test_year_outside_canonical_horizon_is_not_silently_extrapolated(year):
    with pytest.raises(ValueError, match="no entry|unavailable|not available"):
        pe.us.calculate_household(
            **household_inputs(year=year), spm={"geography_kind": "national"}
        )
