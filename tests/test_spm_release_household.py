"""Actual public-wrapper acceptance for explicit, immutable SPM releases.

Run against a development country model with
POLICYENGINE_US_HOUSEHOLD_ONLY=1; no population certification is implied.
"""

import json
import os

import pytest

if os.environ.get("POLICYENGINE_US_HOUSEHOLD_ONLY") != "1":
    pytest.skip(
        "Development SPM release acceptance runs in the dedicated integration job",
        allow_module_level=True,
    )

from spm_calculator.release import load_release, seal_release

import policyengine as pe
from policyengine.tax_benefit_models.us.spm_release import SPMReleaseSelection

EXTRAS = [
    "spm_unit_reference_spm_threshold",
    "spm_unit_unadjusted_spm_threshold",
    "spm_unit_spm_threshold",
    "spm_unit_spm_threshold_housing_portion",
    "spm_unit_capped_housing_subsidy",
    "spm_unit_count_adults",
    "spm_unit_count_children",
    "spm_unit_geographic_adjustment",
]


def household(**kwargs):
    options = {
        "people": [{"age": 40}, {"age": 40}, {"age": 8}, {"age": 5}],
        "spm_unit": {"spm_unit_tenure_type": "RENTER"},
        "household": {"state_code": "TX"},
        "year": 2025,
        "extra_variables": EXTRAS,
        "spm_release": SPMReleaseSelection(),
    }
    options.update(kwargs)
    return pe.us.calculate_household(**options)


def synthetic_selection(tmp_path, *, year=2025, amount=40000, share=0.4):
    doc = load_release().to_dict()
    doc["release_id"] = f"synthetic-{year}-{amount}-{share}"
    entry = doc["years"]["2025"].copy()
    entry.update(methodology_id="synthetic-integration-test")
    entry["thresholds"] = dict.fromkeys(entry["thresholds"], amount)
    entry["housing_shares"] = dict.fromkeys(entry["housing_shares"], share)
    entry["housing_share_provenance"] = dict(
        entry["housing_share_provenance"],
        status="assumed",
        note="Synthetic fixture, not an official share",
    )
    doc["years"] = {str(year): entry}
    doc = seal_release(doc)
    path = tmp_path / f"{doc['release_id']}.json"
    path.write_text(json.dumps(doc))
    return SPMReleaseSelection(path=str(path), expected_sha256=doc["content_sha256"])


def test_published_threshold_runs_through_public_wrapper():
    result = household()
    # Full precision, independently sourced BLS 2025 workbook reference.
    assert result.spm_unit.spm_unit_spm_threshold == pytest.approx(
        41700.555713, abs=0.01
    )
    assert result.provenance["spm"]["years"]["2025"]["status"] == "published"
    assert result.provenance["spm"]["population_data_certified"] is False
    assert json.loads(json.dumps(result.to_dict()))["provenance"] == result.provenance


def test_extrapolated_threshold_has_actual_cpi_and_carried_share_receipt():
    with pytest.warns(UserWarning, match="consumer extrapolation"):
        result = household(
            year=2026,
            spm_unit={
                "spm_unit_tenure_type": "RENTER",
                "housing_assistance": 100000,
                "hud_ttp": 0,
            },
        )
    receipt = result.provenance["spm"]["years"]["2026"]
    assert receipt["status"] == "consumer_extrapolation"
    assert receipt["method"] == "pe_cpi_u"
    assert receipt["cpi"]["target"]["year"] == 2026
    assert result.spm_unit.spm_unit_reference_spm_threshold == pytest.approx(
        41700.555713 * receipt["cpi"]["ratio"], abs=0.01
    )
    assert receipt["housing_share_provenance"]["carried_from_threshold_year"] == 2025
    assert receipt["housing_share_provenance"]["reference_year"] == 2024
    assert result.spm_unit.spm_unit_capped_housing_subsidy == pytest.approx(
        result.spm_unit.spm_unit_reference_spm_threshold
        * receipt["housing_shares"]["renter"],
        abs=0.01,
    )


def test_interleaved_release_and_composition_changes_do_not_leak(tmp_path):
    first = synthetic_selection(tmp_path, amount=40000)
    second = synthetic_selection(tmp_path, amount=50000)
    assert household(spm_release=first).spm_unit.spm_unit_spm_threshold == 40000
    assert household(spm_release=second).spm_unit.spm_unit_spm_threshold == 50000
    assert household(spm_release=first).spm_unit.spm_unit_spm_threshold == 40000
    changed = household(
        spm_release=first, people=[{"age": 40}, {"age": 40}, {"age": 18}, {"age": 5}]
    )
    assert changed.spm_unit.spm_unit_count_adults == 3
    assert changed.spm_unit.spm_unit_count_children == 1
    assert changed.spm_unit.spm_unit_spm_threshold > 40000


def test_year_specific_share_changes_housing_cap_and_resources(tmp_path):
    low = synthetic_selection(tmp_path, year=2025, share=0.3)
    high = synthetic_selection(tmp_path, year=2026, share=0.6)
    spm = {"spm_unit_tenure_type": "RENTER", "housing_assistance": 100000, "hud_ttp": 0}
    before = household(spm_release=low, spm_unit=spm)
    after = household(year=2026, spm_release=high, spm_unit=spm)
    assert before.spm_unit.spm_unit_spm_threshold_housing_portion == pytest.approx(
        12000, abs=0.01
    )
    assert after.spm_unit.spm_unit_spm_threshold_housing_portion == pytest.approx(
        24000, abs=0.01
    )
    assert before.spm_unit.spm_unit_capped_housing_subsidy == pytest.approx(
        12000, abs=0.01
    )
    assert after.spm_unit.spm_unit_capped_housing_subsidy == pytest.approx(
        24000, abs=0.01
    )
    # Hold the model year fixed to isolate the share's effect on resources.
    same_year_low_share = household(
        year=2026,
        spm_unit=spm,
        spm_release=synthetic_selection(tmp_path, year=2026, share=0.3),
    )
    assert (
        after.spm_unit.spm_unit_net_income
        - same_year_low_share.spm_unit.spm_unit_net_income
        == pytest.approx(12000, abs=0.01)
    )


def test_baked_threshold_is_rejected_before_calculation():
    with pytest.raises(ValueError, match="computed outputs"):
        household(spm_unit={"spm_unit_spm_threshold": 123})


def test_poverty_equality_uses_derived_resources(tmp_path):
    people = [
        {"age": 40, "employment_income": 80000},
        {"age": 40},
        {"age": 8},
        {"age": 5},
    ]
    reference = household(people=people)
    resources = reference.spm_unit.spm_unit_net_income
    equal = household(
        people=people, spm_release=synthetic_selection(tmp_path, amount=resources)
    )
    assert equal.spm_unit.spm_unit_net_income == equal.spm_unit.spm_unit_spm_threshold
    assert equal.spm_unit.spm_unit_is_in_spm_poverty == 0
    below = household(
        people=people, spm_release=synthetic_selection(tmp_path, amount=resources + 1)
    )
    assert below.spm_unit.spm_unit_is_in_spm_poverty == 1


def test_pinned_geography_matches_standalone_and_fallback_is_visible():
    from spm_calculator.release import SPMUnit

    release = load_release()
    expected = release.calculate_unit(
        SPMUnit(
            unit_id="u",
            num_adults=2,
            num_children=2,
            tenure="owner_with_mortgage",
            year=2025,
            geography_kind="congressional_district",
            geography_id="101",
        )
    )
    result = household(
        spm_unit={"spm_unit_tenure_type": "OWNER_WITH_MORTGAGE"},
        household={"state_code": "AL", "congressional_district_geoid": 101},
        spm_release=SPMReleaseSelection(geography_kind="congressional_district"),
    )
    assert result.spm_unit.spm_unit_spm_threshold == pytest.approx(
        expected["threshold"], abs=0.01
    )
    receipt = result.provenance["spm"]["geographies"][0]
    assert (
        receipt["geography_release_id"]
        == expected["provenance"]["geography"]["geography_release_id"]
    )
    with pytest.raises(ValueError, match="unavailable"):
        household(
            spm_release=SPMReleaseSelection(geography_kind="congressional_district")
        )
    fallback = household(
        spm_release=SPMReleaseSelection(
            geography_kind="congressional_district", missing_geography="national"
        )
    )
    assert (
        fallback.provenance["spm"]["geographies"][0]["status"]
        == "explicit_national_fallback"
    )


def test_existing_default_result_has_no_spm_provider_provenance():
    result = pe.us.calculate_household(people=[{"age": 40}], year=2025)
    assert "provenance" not in result


def test_development_model_has_no_data_certification_and_rejects_population():
    if not getattr(pe.us.model, "household_only", False):
        pytest.skip(
            "Only applicable to explicit household-only development registration"
        )
    assert pe.us.model.release_manifest is None
    assert pe.us.model.data_certification is None
    with pytest.raises(ValueError, match="household-only"):
        pe.us.model.run(None)
    with pytest.raises(ValueError, match="household-only"):
        pe.us.managed_microsimulation()
    with pytest.raises(ValueError, match="manifest"):
        _ = pe.us.model.trace_tro


def test_minor_only_unit_requires_classification_instead_of_zero_threshold():
    with pytest.raises(ValueError, match="at least one classified SPM adult"):
        household(people=[{"age": 12}])
