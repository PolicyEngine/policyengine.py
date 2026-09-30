"""Default SPM geography for household calculations.

With no ``geography_kind`` chosen, ``calculate_household`` measures a household
in its county's SPM estimation area when it has ``county_fips``, and nationally
when it names no county, reporting the substitution in provenance. The unit
tests check the selection logic against a stub bundle; the household tests run
the real pinned country model and calculator.

Invariants checked here, for every household that names no county:

- the default calculation never raises ``SPMInputError``;
- it equals the explicit national calculation, output for output, apart from
  ``spm_geography_source``;
- its geographic adjustment is exactly 1 and its threshold equals the
  unadjusted threshold;
- SPM poverty is exactly ``spm_unit_net_income < spm_unit_spm_threshold``.

A household with ``county_fips`` equals the explicit county calculation.
"""

import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# The household cases run the real pinned country model and calculator, never a
# substitute; skip only if they are absent from the environment.
pytest.importorskip("policyengine_us")
pytest.importorskip("spm_calculator.policyengine_adapter")

from policyengine_us.variables.household.demographic.geographic.state_code import (  # noqa: E402
    StateCode,
)
from spm_calculator.errors import SPMInputError  # noqa: E402

import policyengine as pe  # noqa: E402
from policyengine.tax_benefit_models.us.household import _names_county  # noqa: E402
from policyengine.tax_benefit_models.us.spm import (  # noqa: E402
    SPM_GEOGRAPHY_SOURCES,
    SPMSelection,
    resolve_household_spm_selection,
    resolve_spm_selection,
)

ARTIFACT = "a" * 64


@pytest.fixture
def county_bundle(monkeypatch):
    value = {
        "measurements": {
            "spm": {
                "forecast_content_sha256": ARTIFACT,
                "scenario": "ce_trend",
                "geography_kind": "county",
            }
        }
    }
    monkeypatch.setattr("policyengine.bundle.get_current_bundle", lambda: value)
    return value


def test_household_without_county_falls_back_to_national(county_bundle):
    config, source = resolve_household_spm_selection(None, household_names_county=False)
    assert source == "national_fallback"
    assert config == resolve_spm_selection({"geography_kind": "national"})
    assert config["geography_kind"] == "national"
    assert config["forecast_content_sha256"] == ARTIFACT


def test_household_with_county_keeps_the_default(county_bundle):
    config, source = resolve_household_spm_selection(None, household_names_county=True)
    assert source == "default"
    assert config == resolve_spm_selection()
    assert config["geography_kind"] == "county"


@pytest.mark.parametrize("names_county", [False, True])
@pytest.mark.parametrize(
    "selection",
    [
        {"geography_kind": "county"},
        {"geography_kind": "national"},
        {"geography_kind": "metro", "geography_id": "31080"},
        SPMSelection(geography_kind="county"),
    ],
)
def test_chosen_geography_is_used_as_given(county_bundle, selection, names_county):
    config, source = resolve_household_spm_selection(
        selection, household_names_county=names_county
    )
    assert source == "selection"
    assert config == resolve_spm_selection(selection)


def test_fallback_keeps_the_other_chosen_settings(county_bundle):
    selection = {"scenario": "zero_real", "as_of": "2026-09-09"}
    config, source = resolve_household_spm_selection(
        selection, household_names_county=False
    )
    assert source == "national_fallback"
    assert config == resolve_spm_selection({**selection, "geography_kind": "national"})
    assert config["scenario"] == "zero_real"
    assert config["as_of"] == "2026-09-09"


def test_fallback_is_only_for_the_county_default(county_bundle):
    county_bundle["measurements"]["spm"]["geography_kind"] = "national"
    config, source = resolve_household_spm_selection(None, household_names_county=False)
    assert source == "default"
    assert config == resolve_spm_selection()


def test_sources_are_the_documented_set(county_bundle):
    seen = {
        resolve_household_spm_selection(selection, household_names_county=names)[1]
        for selection in (None, {"geography_kind": "national"})
        for names in (False, True)
    }
    assert seen == set(SPM_GEOGRAPHY_SOURCES)


@pytest.mark.parametrize(
    "household,axes,expected",
    [
        ({"state_code": "CA"}, None, False),
        ({"state_code": "CA", "county_fips": None}, None, False),
        ({"state_code": "CA", "county_fips": ""}, None, False),
        ({"state_code": "CA", "county_fips": "06037"}, None, True),
        # Malformed codes still name a county, so they reach the typed error.
        ({"state_code": "CA", "county_fips": 6037}, None, True),
        ({"state_code": "CA", "county_fips": "6037"}, None, True),
        ({"state_code": "CA", "county": "LOS_ANGELES_COUNTY_CA"}, None, True),
        ({"state_code": "CA", "county_str": "LOS_ANGELES_COUNTY_CA"}, None, True),
        (
            {"state_code": "CA"},
            [[{"name": "employment_income", "min": 0, "max": 1, "count": 2}]],
            False,
        ),
        (
            {"state_code": "CA"},
            [[{"name": "county_fips", "min": 0, "max": 1, "count": 2}]],
            True,
        ),
    ],
)
def test_names_county(household, axes, expected):
    assert _names_county(household, axes) is expected


# Household calculations against the pinned country model and calculator.

MEASUREMENT = [
    "spm_unit_spm_threshold",
    "spm_unit_unadjusted_spm_threshold",
    "spm_unit_geographic_adjustment",
]
STATE_CODES = [state.name for state in StateCode]
# policyengine-us 2.2.1 has no SNAP region for Puerto Rico, so every Puerto
# Rico household calculation fails before any SPM formula runs, whatever the
# SPM geography.
FAILS_OUTSIDE_SPM = {"PR": ValueError}


def household(state_code="CA", *, earnings=50_000, children=1, **location):
    return {
        "people": [
            {"age": 40, "employment_income": earnings},
            *({"age": 8} for _ in range(children)),
        ],
        "tax_unit": {"filing_status": "HEAD_OF_HOUSEHOLD" if children else "SINGLE"},
        "household": {"state_code": state_code, **location},
        "year": 2026,
    }


def calculate(inputs, spm=None, *, tenure=None):
    inputs = dict(inputs)
    if tenure is not None:
        inputs["spm_unit"] = {"spm_unit_tenure_type": tenure}
    return pe.us.calculate_household(
        **inputs, spm=spm, extra_variables=MEASUREMENT
    ).to_dict()


def without_source(result):
    provenance = dict(result["provenance"])
    provenance.pop("spm_geography_source")
    return {**result, "provenance": provenance}


def check_national_fallback(result):
    provenance = result["provenance"]
    assert provenance["spm_geography_source"] == "national_fallback"
    assert provenance["spm_config"]["geography_kind"] == "national"
    assert provenance["spm"]["geography_kind"] == "national"
    unit = result["spm_unit"]
    assert unit["spm_unit_geographic_adjustment"] == 1.0
    assert unit["spm_unit_spm_threshold"] == unit["spm_unit_unadjusted_spm_threshold"]
    assert unit["spm_unit_spm_threshold"] > 0
    assert math.isfinite(unit["spm_unit_net_income"])
    in_poverty = unit["spm_unit_net_income"] < unit["spm_unit_spm_threshold"]
    assert bool(unit["spm_unit_is_in_spm_poverty"]) is in_poverty


def test_state_only_household_returns_a_national_result():
    """The regression: a state-only household used to raise SPMInputError."""
    result = calculate(household("CA"))
    check_national_fallback(result)
    assert result["household"]["household_net_income"] > 0
    assert math.isfinite(result["tax_unit"]["income_tax"])


@pytest.mark.parametrize("state_code", ["CA", "MS", "NY"])
def test_state_only_default_equals_explicit_national(state_code):
    inputs = household(state_code)
    default = calculate(inputs)
    explicit = calculate(inputs, {"geography_kind": "national"})
    assert explicit["provenance"]["spm_geography_source"] == "selection"
    assert without_source(default) == without_source(explicit)


def test_blank_county_fips_is_no_county():
    result = calculate(household("CA", county_fips=""))
    check_national_fallback(result)
    assert without_source(result) == without_source(calculate(household("CA")))


def test_fallback_keeps_a_chosen_scenario():
    inputs = household("TX")
    default = calculate(inputs, {"scenario": "zero_real"})
    check_national_fallback(default)
    assert default["provenance"]["spm_config"]["scenario"] == "zero_real"
    explicit = calculate(
        inputs, {"geography_kind": "national", "scenario": "zero_real"}
    )
    assert without_source(default) == without_source(explicit)


@pytest.mark.parametrize("county_fips", ["06037", "28001", "36061"])
def test_county_household_default_equals_explicit_county(county_fips):
    state_code = {"06": "CA", "28": "MS", "36": "NY"}[county_fips[:2]]
    inputs = household(state_code, county_fips=county_fips)
    default = calculate(inputs)
    explicit = calculate(inputs, {"geography_kind": "county"})
    assert default["provenance"]["spm_geography_source"] == "default"
    assert default["provenance"]["spm_config"]["geography_kind"] == "county"
    assert without_source(default) == without_source(explicit)
    assignment = default["provenance"]["spm"]["geographies"][0]["county_assignment"]
    assert assignment is not None


def test_county_adjustment_differs_from_national_where_rents_do():
    """Los Angeles County's area adjustment is used, not the national one."""
    county = calculate(household("CA", county_fips="06037"))
    national = calculate(household("CA"))
    county_unit, national_unit = county["spm_unit"], national["spm_unit"]
    assert county_unit["spm_unit_geographic_adjustment"] > 1
    assert (
        county_unit["spm_unit_spm_threshold"] > national_unit["spm_unit_spm_threshold"]
    )
    assert (
        county_unit["spm_unit_unadjusted_spm_threshold"]
        == national_unit["spm_unit_unadjusted_spm_threshold"]
    )


@pytest.mark.parametrize("state_code", STATE_CODES)
def test_every_state_code_without_county_computes(state_code):
    inputs = household(state_code)
    expected_error = FAILS_OUTSIDE_SPM.get(state_code)
    if expected_error is not None:
        # The same failure with or without the fallback, and never an SPM one.
        for spm in (None, {"geography_kind": "national"}):
            with pytest.raises(expected_error) as caught:
                calculate(inputs, spm)
            assert not isinstance(caught.value, SPMInputError)
        return
    check_national_fallback(calculate(inputs))


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    state_code=st.sampled_from(
        [code for code in STATE_CODES if code not in FAILS_OUTSIDE_SPM]
    ),
    earnings=st.integers(min_value=0, max_value=250_000),
    children=st.integers(min_value=0, max_value=3),
    tenure=st.sampled_from(
        [None, "RENTER", "OWNER_WITH_MORTGAGE", "OWNER_WITHOUT_MORTGAGE"]
    ),
)
def test_no_county_is_always_the_explicit_national_result(
    state_code, earnings, children, tenure
):
    inputs = household(state_code, earnings=earnings, children=children)
    default = calculate(inputs, tenure=tenure)
    check_national_fallback(default)
    explicit = calculate(inputs, {"geography_kind": "national"}, tenure=tenure)
    assert without_source(default) == without_source(explicit)
