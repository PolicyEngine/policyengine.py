"""The Simulation adapter for disclosure-controlled UK geography outputs.

All data here is synthetic.
"""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine import outputs
from policyengine.disclosure import (
    NOISE_KEY_ENV,
    AreaWeights,
    DisclosureError,
    DisclosureKeyError,
    DisclosureSettings,
    PublicTable,
    validate_public,
)
from policyengine.outputs.uk_geography_disclosure import (
    UKGeographyDisclosure,
    compute_uk_geography_disclosure,
)

TEST_KEY = "test-key-for-unit-tests-only"
SEATS = {"S1": "NORTH_EAST", "S2": "NORTH_EAST", "S3": "LONDON", "S4": "LONDON"}


def _make_sim(household_data: dict) -> MagicMock:
    """Create a mock Simulation with household-level data."""
    hh_df = MicroDataFrame(pd.DataFrame(household_data), weights="household_weight")
    sim = MagicMock()
    sim.output_dataset.data.household = hh_df
    sim.id = "test-sim"
    return sim


def _households(affected=None, *, per_seat=150):
    affected = affected or dict.fromkeys(SEATS, 80)
    rng = np.random.default_rng(0)
    seats, regions, deltas = [], [], []
    for seat, region in SEATS.items():
        seats += [seat] * per_seat
        regions += [region] * per_seat
        deltas += list(rng.uniform(100.0, 900.0, affected[seat]))
        deltas += [0.0] * (per_seat - affected[seat])
    n = len(seats)
    baseline = {
        "household_id": np.arange(n),
        "household_weight": np.full(n, 100.0),
        "household_net_income": rng.uniform(20_000.0, 60_000.0, n),
        "region": regions,
        "constituency_code_oa": seats,
        "source_household_id": np.arange(n) + 5_000,
    }
    reform = {
        **baseline,
        "household_net_income": baseline["household_net_income"] + np.array(deltas),
    }
    return baseline, reform


def _compute(baseline, reform, **options):
    options.setdefault("year", 2026)
    return compute_uk_geography_disclosure(
        _make_sim(baseline), _make_sim(reform), **options
    )


def test_regions_are_published_with_intervals_and_pass_the_validator():
    impact = _compute(*_households())

    frame = impact.public.to_frame()

    assert isinstance(impact, UKGeographyDisclosure)
    assert impact.findings == []
    assert set(frame["level"]) == {"region"}
    assert set(frame["area_code"]) == {"NORTH_EAST", "LONDON"}
    averages = frame[frame["outcome"] == "average_change"]
    assert (averages["tier"] == "reported").all()
    assert (averages["lo"] <= averages["value"]).all()
    assert (averages["value"] <= averages["hi"]).all()
    assert validate_public(impact.public) == []


def test_public_rows_round_trip_through_json():
    impact = _compute(*_households(), levels=("national", "region", "constituency"))

    restored = PublicTable.model_validate_json(impact.public.model_dump_json())

    assert restored == impact.public
    assert set(impact.public.to_frame()["level"]) == {
        "national",
        "region",
        "constituency",
    }
    assert set(impact.public.to_frame().query("level == 'national'")["area_code"]) == {
        "UK"
    }


def test_region_codes_are_preferred_over_the_stored_region():
    baseline, reform = _households()
    codes = [
        "E12000001" if r == "NORTH_EAST" else "E12000007" for r in baseline["region"]
    ]
    baseline["region_code_oa"] = codes
    reform["region_code_oa"] = codes

    impact = _compute(baseline, reform)

    assert set(impact.public.to_frame()["area_code"]) == {"E12000001", "E12000007"}


def test_a_dataset_without_a_source_id_is_refused_unless_ids_are_passed():
    baseline, reform = _households()
    ids = baseline.pop("source_household_id")
    reform.pop("source_household_id")

    with pytest.raises(ValueError, match="source_ids="):
        _compute(baseline, reform)

    impact = _compute(baseline, reform, source_ids=ids)
    assert impact.public is not None


def test_passed_ids_count_clones_once():
    baseline, reform = _households()
    clones = np.arange(len(baseline["household_id"])) // 30

    impact = _compute(baseline, reform, source_ids=clones, levels=("constituency",))

    assert (
        impact.public is None
        or (
            impact.public.to_frame().query("outcome == 'average_change'")["tier"]
            == "withheld"
        ).all()
    )


def test_a_thin_seat_blocks_publication_until_it_is_resolved():
    baseline, reform = _households({"S1": 4, "S2": 40, "S3": 80, "S4": 80})

    impact = _compute(baseline, reform, levels=("constituency",))

    assert impact.public is None
    blocking = [finding for finding in impact.findings if finding.blocking]
    assert {finding.code for finding in blocking} == {"recoverable_remainder"}
    assert {finding.suggested for finding in blocking} == {"S2"}
    for outcome in ("average_change", "share_gaining"):
        impact.release.withhold(
            level="constituency",
            area_code="S2",
            reform="reform",
            year=2026,
            outcome=outcome,
        )
    public = impact.refresh()
    assert impact.public is public
    assert impact.findings == []
    tiers = public.to_frame().query("outcome == 'average_change'")
    assert dict(zip(tiers["area_code"], tiers["tier"])) == {
        "S1": "withheld",
        "S2": "withheld",
        "S3": "reported",
        "S4": "reported",
    }


def test_frames_must_hold_the_same_households_in_the_same_order():
    baseline, reform = _households()
    reform["household_id"] = reform["household_id"][::-1]

    with pytest.raises(ValueError, match="same order"):
        _compute(baseline, reform)

    baseline, reform = _households()
    with pytest.raises(ValueError, match="household_net_income"):
        _compute(baseline, {k: v for k, v in reform.items() if "income" not in k})


def test_an_unknown_or_missing_level_raises():
    baseline, reform = _households()

    with pytest.raises(ValueError, match="Unknown level"):
        _compute(baseline, reform, levels=("ward",))
    with pytest.raises(ValueError, match="la_code_oa"):
        _compute(baseline, reform, levels=("local_authority",))


def test_seats_and_local_authorities_together_need_an_acknowledgement():
    baseline, reform = _households()
    authorities = [
        "L1" if s in ("S1", "S3") else "L2" for s in baseline["constituency_code_oa"]
    ]
    regions = ["R"] * len(authorities)
    for frame in (baseline, reform):
        frame["la_code_oa"] = authorities
        frame["region"] = regions
    levels = ("constituency", "local_authority")

    blocked = _compute(baseline, reform, levels=levels)
    accepted = _compute(
        baseline, reform, levels=levels, acknowledge=["unchecked_overlap"]
    )

    assert blocked.public is None
    assert [finding.code for finding in blocked.findings] == ["unchecked_overlap"]
    assert accepted.public is not None


def test_noise_needs_a_key_and_the_key_never_reaches_the_results(monkeypatch):
    monkeypatch.delenv(NOISE_KEY_ENV, raising=False)
    baseline, reform = _households()
    settings = DisclosureSettings(noise=True)

    with pytest.raises(DisclosureKeyError):
        _compute(baseline, reform, settings=settings)

    impact = _compute(baseline, reform, settings=settings, noise_key=TEST_KEY)
    plain = _compute(baseline, reform)

    assert impact.public.to_frame()["noise"].all()
    assert not plain.public.to_frame()["noise"].any()
    assert TEST_KEY not in impact.public.model_dump_json()
    assert TEST_KEY not in repr(impact.__dict__)
    assert TEST_KEY not in repr(impact.__pydantic_private__)
    assert TEST_KEY not in repr(vars(impact.release))


def test_a_weight_matrix_can_replace_the_area_codes():
    baseline, reform = _households()
    n = len(baseline["household_id"])
    matrix = AreaWeights.from_matrix(np.full((2, n), 50.0), ["M1", "M2"])

    options = {"levels": ("constituency",), "area_weights": {"constituency": matrix}}

    with pytest.raises(ValueError, match="parent_of"):
        _compute(baseline, reform, **options)

    impact = _compute(
        baseline,
        reform,
        parent_of={"constituency": {"M1": "NORTH_EAST", "M2": "LONDON"}},
        **options,
    )
    assert set(impact.public.to_frame()["area_code"]) == {"M1", "M2"}


def test_the_audit_goes_to_a_private_directory_outside_repositories(tmp_path):
    baseline, reform = _households()
    repository = tmp_path / "repo"
    (repository / ".git").mkdir(parents=True)

    with pytest.raises(DisclosureError, match="git repository"):
        _compute(baseline, reform, audit_dir=repository / "audit")

    _compute(baseline, reform, audit_dir=tmp_path / "audit")
    assert (tmp_path / "audit" / "disclosure_audit.csv").exists()


def test_the_release_is_available_only_after_a_run():
    impact = UKGeographyDisclosure.model_construct(
        baseline_simulation=MagicMock(), reform_simulation=MagicMock(), year=2026
    )

    with pytest.raises(ValueError, match=r"run\(\) first"):
        _ = impact.release


def test_the_adapter_is_exported_from_outputs():
    assert outputs.UKGeographyDisclosure is UKGeographyDisclosure
    assert outputs.compute_uk_geography_disclosure is compute_uk_geography_disclosure
