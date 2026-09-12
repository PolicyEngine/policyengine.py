"""The wrapper pins measurement provenance and accepts explicit locations."""

import json

import pytest
from pydantic import ValidationError

import policyengine as pe
from policyengine.tax_benefit_models.us.spm import SPMSelection, resolve_spm_selection


@pytest.fixture
def pinned_bundle(monkeypatch):
    value = {
        "measurements": {
            "spm": {
                "forecast_content_sha256": "a" * 64,
                "scenario": "ce_trend",
                "geography_kind": "county",
            }
        }
    }
    monkeypatch.setattr("policyengine.bundle.get_current_bundle", lambda: value)
    return value


def test_default_selection_preserves_independent_bundle_hash(pinned_bundle):
    config = resolve_spm_selection()
    assert config["forecast_content_sha256"] == "a" * 64
    assert config["geography_kind"] == "county"
    assert config["scenario"] == "ce_trend"
    assert SPMSelection.model_validate_json(json.dumps(config)).model_dump() == config


def test_explicit_national_and_scenario_do_not_replace_artifact(pinned_bundle):
    config = resolve_spm_selection(
        SPMSelection(geography_kind="national", scenario="zero_real")
    )
    assert config["forecast_content_sha256"] == "a" * 64
    assert config["geography_kind"] == "national"
    assert config["scenario"] == "zero_real"
    assert pinned_bundle["measurements"]["spm"]["scenario"] == "ce_trend"


def test_no_null_or_unmatched_digest_bypass(pinned_bundle):
    assert (
        resolve_spm_selection({"forecast_content_sha256": None})[
            "forecast_content_sha256"
        ]
        == "a" * 64
    )
    with pytest.raises(ValueError, match="artifact hash"):
        resolve_spm_selection({"forecast_content_sha256": "b" * 64})
    pinned_bundle["measurements"]["spm"].pop("forecast_content_sha256")
    with pytest.raises(ValueError, match="must pin"):
        resolve_spm_selection()


@pytest.mark.parametrize(
    "value",
    [
        {"geography_kind": "state"},
        {"geography_kind": "congressional_district"},
        {"geography_kind": "national", "geography_id": "A"},
        {"geography_kind": "metro"},
        {"year_policy": "pe_cpi_u"},
        {"allow_estimated": True},
        {"path": "/tmp/other.json"},
    ],
)
def test_old_fallback_policies_and_ambiguous_locations_rejected(value):
    with pytest.raises(ValidationError):
        SPMSelection.model_validate(value)


def test_missing_bundle_configuration_is_not_silently_inferred(monkeypatch):
    monkeypatch.setattr("policyengine.bundle.get_current_bundle", lambda: {})
    with pytest.raises(ValueError, match="no certified SPM"):
        resolve_spm_selection()


@pytest.mark.parametrize("value", [[], "", False, 0])
def test_falsey_non_selection_is_rejected(pinned_bundle, value):
    with pytest.raises(ValidationError):
        resolve_spm_selection(value)


@pytest.mark.parametrize(
    "value",
    [
        {"scenario": ""},
        {"scenario": " "},
        {"county_vintage": ""},
        {"county_vintage": 2020},
        {"as_of": "2026-02-30"},
        {"as_of": "20260909"},
        {"as_of": "2026-09-09T00:00:00"},
    ],
)
def test_malformed_selection_values_rejected(value):
    with pytest.raises(ValidationError):
        SPMSelection.model_validate(value)


def test_switching_explicit_geography_drops_default_area(pinned_bundle):
    pinned_bundle["measurements"]["spm"].update(
        geography_kind="metro", geography_id="12345"
    )
    config = resolve_spm_selection({"geography_kind": "national"})
    assert config["geography_id"] is None
    assert config["geography_kind"] == "national"


@pytest.mark.parametrize("geography_kind", ["county", "national", "metro"])
def test_partial_selection_preserves_omissions_in_public_round_trips(
    pinned_bundle, geography_kind
):
    pinned_bundle["measurements"]["spm"].update(
        geography_kind=geography_kind,
        geography_id="12345" if geography_kind == "metro" else None,
        county_vintage="2010",
        as_of="2026-06-01",
    )
    selection = SPMSelection(scenario="zero_real")
    envelope = pe.Simulation(spm=selection)
    nested_json = envelope.model_dump_json(include={"spm"})
    assert json.loads(nested_json) == {"spm": {"scenario": "zero_real"}}
    restored_selections = [
        SPMSelection.model_validate(selection.model_dump()),
        SPMSelection.model_validate_json(selection.model_dump_json()),
        pe.Simulation.model_validate_json(nested_json).spm,
    ]
    expected = resolve_spm_selection(selection)
    for restored in restored_selections:
        assert restored.model_fields_set == {"scenario"}
        assert resolve_spm_selection(restored) == expected
        assert resolve_spm_selection(restored)["geography_kind"] == geography_kind
        assert resolve_spm_selection(restored)["county_vintage"] == "2010"
        assert resolve_spm_selection(restored)["as_of"] == "2026-06-01"


@pytest.mark.parametrize("geography_kind", ["national", "metro"])
def test_resolved_selection_retains_all_settings_after_public_json_round_trip(
    pinned_bundle, geography_kind
):
    defaults = pinned_bundle["measurements"]["spm"]
    defaults.update(
        geography_kind=geography_kind,
        geography_id="12345" if geography_kind == "metro" else None,
    )
    expected = resolve_spm_selection({"scenario": "zero_real"})
    resolved = SPMSelection.model_validate(expected)
    assert set(json.loads(resolved.model_dump_json())) == set(SPMSelection.model_fields)
    restored = pe.Simulation.model_validate_json(
        pe.Simulation(spm=resolved).model_dump_json(include={"spm"})
    ).spm
    defaults.update(
        geography_kind="county",
        geography_id=None,
        scenario="ce_trend",
        county_vintage="2010",
        as_of="2026-06-01",
    )
    assert restored.model_fields_set == set(SPMSelection.model_fields)
    assert resolve_spm_selection(restored) == expected


@pytest.mark.parametrize("geography_kind", ["national", "metro"])
def test_explicit_class_defaults_remain_overrides_after_json_round_trip(
    pinned_bundle, geography_kind
):
    pinned_bundle["measurements"]["spm"].update(
        geography_kind=geography_kind,
        geography_id="12345" if geography_kind == "metro" else None,
        county_vintage="2010",
        as_of="2026-06-01",
    )
    selection = SPMSelection(geography_kind="county", county_vintage="2020", as_of=None)
    restored = SPMSelection.model_validate_json(selection.model_dump_json())
    config = resolve_spm_selection(restored)
    assert config["geography_kind"] == "county"
    assert config["geography_id"] is None
    assert config["county_vintage"] == "2020"
    assert config["as_of"] is None


@pytest.mark.parametrize("geography_kind", ["national", "metro"])
def test_partial_selection_json_round_trip_preserves_real_household_threshold(
    monkeypatch, geography_kind
):
    """State-only inputs must still use the inherited national or metro area."""
    pytest.importorskip("spm_calculator.policyengine_adapter")
    pytest.importorskip("policyengine_us.spm")
    import numpy as np
    from spm_calculator.release import SPMUnit
    from spm_calculator.rolling_forecast import load_forecast

    from policyengine import bundle

    configured = bundle.get_current_bundle()
    forecast = load_forecast()
    area_id = (
        forecast.resolve_county(2026, "06037", scenario="zero_real")["area_id"]
        if geography_kind == "metro"
        else None
    )
    configured["measurements"]["spm"].update(
        geography_kind=geography_kind, geography_id=area_id
    )
    monkeypatch.setattr(bundle, "get_current_bundle", lambda: configured)
    selection = SPMSelection(scenario="zero_real")
    restored_selections = [
        selection,
        SPMSelection.model_validate_json(selection.model_dump_json()),
        pe.Simulation.model_validate_json(
            pe.Simulation(spm=selection).model_dump_json(include={"spm"})
        ).spm,
    ]
    expected = forecast.calculate_unit(
        SPMUnit(
            unit_id="selection-round-trip",
            year=2026,
            num_adults=1,
            num_children=0,
            tenure="renter",
            geography_kind=geography_kind,
            geography_id=area_id,
        ),
        scenario="zero_real",
    )
    for restored in restored_selections:
        result = pe.us.calculate_household(
            people=[{"age": 40, "employment_income": 50_000}],
            tax_unit={"filing_status": "SINGLE"},
            spm_unit={"spm_unit_tenure_type": "RENTER"},
            household={"state_code": "CA"},
            year=2026,
            spm=restored,
            extra_variables=["spm_unit_spm_threshold"],
        )
        assert result.spm_unit.spm_unit_spm_threshold == float(
            np.float32(expected["threshold"])
        )
        assert result.to_dict()["provenance"]["spm_config"] == resolve_spm_selection(
            selection
        )
        assert result.to_dict()["provenance"]["spm"]["geography_kind"] == geography_kind
