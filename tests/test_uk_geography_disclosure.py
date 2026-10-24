"""The Simulation adapter for disclosure-controlled UK geography outputs.

All data here is synthetic.
"""

from enum import Enum
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine import outputs
from policyengine.countries.uk.regions import ENGLISH_REGIONS
from policyengine.disclosure import (
    NOISE_KEY_ENV,
    AreaWeights,
    DisclosureError,
    DisclosureKeyError,
    DisclosureSettings,
    PriorPublic,
    PublicTable,
    validate_public,
)
from policyengine.outputs.uk_geography_disclosure import (
    UK_REGION_GSS_CODES,
    UKGeographyDisclosure,
    compute_uk_geography_disclosure,
)

TEST_KEY = "test-key-for-unit-tests-only"
SEATS = {"S1": "NORTH_EAST", "S2": "NORTH_EAST", "S3": "LONDON", "S4": "LONDON"}
NATIONS = {
    "S1": "NORTH_EAST",
    "S2": "WALES",
    "S3": "SCOTLAND",
    "S4": "NORTHERN_IRELAND",
}
GSS = {
    "NORTH_EAST": "E12000001",
    "LONDON": "E12000007",
    "WALES": "W92000004",
    "SCOTLAND": "S92000003",
    "NORTHERN_IRELAND": "N92000002",
}
# What Microcosm writes in region_code_oa: GSS codes, pseudo codes for nations.
MICROCOSM = {
    **GSS,
    "WALES": "W99999999",
    "SCOTLAND": "S99999999",
    "NORTHERN_IRELAND": "N99999999",
}


class Region(Enum):
    """Shaped like the engine's region enum: stored names, display values."""

    NORTH_EAST = "North East"
    WALES = "Wales"
    SCOTLAND = "Scotland"
    NORTHERN_IRELAND = "Northern Ireland"
    UNKNOWN = "Unknown"


def _make_sim(household_data: dict) -> MagicMock:
    """Create a mock Simulation with household-level data."""
    hh_df = MicroDataFrame(pd.DataFrame(household_data), weights="household_weight")
    sim = MagicMock()
    sim.output_dataset.data.household = hh_df
    sim.id = "test-sim"
    return sim


def _households(affected=None, *, per_seat=150, region_of=SEATS):
    affected = affected or dict.fromkeys(region_of, 80)
    rng = np.random.default_rng(0)
    seats, regions, deltas = [], [], []
    for seat, region in region_of.items():
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
    assert set(frame["area_code"]) == {"E12000001", "E12000007"}
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


def test_the_region_table_maps_every_stored_region_to_its_gss_code():
    stored = (*ENGLISH_REGIONS, "WALES", "SCOTLAND", "NORTHERN_IRELAND")
    codes = [f"E1200000{number}" for number in range(1, 10)]
    codes += ["W92000004", "S92000003", "N92000002"]

    assert [UK_REGION_GSS_CODES[name] for name in stored] == codes
    assert [UK_REGION_GSS_CODES[code] for code in codes] == codes
    assert [
        UK_REGION_GSS_CODES[code] for code in ("W99999999", "S99999999", "N99999999")
    ] == codes[-3:]
    assert UK_REGION_GSS_CODES["UNKNOWN"] == ""


def test_regions_are_keyed_on_gss_codes_whatever_the_dataset_stores():
    stored = {
        "enum names": ("region", str),
        "bytes": ("region", str.encode),
        "enum members": ("region", Region.__getitem__),
        "GSS codes": ("region_code_oa", GSS.__getitem__),
        "Microcosm codes": ("region_code_oa", MICROCOSM.__getitem__),
    }
    tables = {}
    for name, (column, spell) in stored.items():
        baseline, reform = _households(region_of=NATIONS)
        values = [spell(region) for region in baseline.pop("region")]
        reform.pop("region")
        baseline[column] = reform[column] = values
        tables[name] = _compute(baseline, reform).public.to_frame()

    assert set(tables["enum names"]["area_code"]) == {
        "E12000001",
        "W92000004",
        "S92000003",
        "N92000002",
    }
    for frame in tables.values():
        pd.testing.assert_frame_equal(frame, tables["enum names"])


def test_region_codes_are_preferred_over_the_stored_region():
    baseline, reform = _households()
    codes = [
        "E12000002" if r == "NORTH_EAST" else "E12000008" for r in baseline["region"]
    ]
    baseline["region_code_oa"] = codes
    reform["region_code_oa"] = codes

    impact = _compute(baseline, reform)

    assert set(impact.public.to_frame()["area_code"]) == {"E12000002", "E12000008"}


def test_an_unknown_region_is_in_the_nation_but_in_no_region():
    baseline, reform = _households()
    # The last households of S4 do not change.
    regions = [*baseline["region"][:-30], *[Region.UNKNOWN] * 30]
    baseline["region"] = reform["region"] = regions

    impact = _compute(baseline, reform, levels=("national", "region"))

    assert impact.findings == []
    frame = impact.public.to_frame()
    assert set(frame["area_code"]) == {"UK", "E12000001", "E12000007"}


@pytest.mark.parametrize(
    "column, spelling",
    [
        ("region", "London"),
        ("region", "ENGLAND"),
        ("region", b"Eastern"),
        ("region_code_oa", "E12000010"),
        ("region_code_oa", "E92000001"),
    ],
)
def test_a_value_that_names_no_region_raises(column, spelling):
    baseline, reform = _households()
    values = list(baseline["region"])
    if column == "region_code_oa":
        values = [GSS[name] for name in values]
    values[0] = spelling
    baseline[column] = reform[column] = values

    with pytest.raises(
        ValueError, match=f"in {column} that name no UK region: 1"
    ) as raised:
        _compute(baseline, reform)
    label = spelling.decode() if isinstance(spelling, bytes) else spelling
    assert label not in str(raised.value)


def test_a_regional_release_is_a_prior_for_seats_from_another_dataset():
    """Regions from a national dataset first, then seats from a local file."""
    national = _households()
    regional = _compute(*national).public.to_frame()
    local_baseline, local_reform = _households()
    codes = [MICROCOSM[name] for name in local_baseline["region"]]
    local_baseline["region_code_oa"] = local_reform["region_code_oa"] = codes
    seats = {"levels": ("constituency",)}

    prior = PriorPublic.from_frame("regional release", regional)
    impact = _compute(local_baseline, local_reform, prior_public=[prior], **seats)

    assert impact.findings == []
    # The same table under the engine's names would match no region.
    names = regional.replace({"area_code": {v: k for k, v in GSS.items()}})
    stale = PriorPublic.from_frame("regional release", names)
    with pytest.raises(DisclosureError, match="name no region area of the release"):
        _compute(local_baseline, local_reform, prior_public=[stale], **seats)


def test_a_prior_cell_at_a_level_that_is_not_a_uk_level_raises():
    """A misspelt level would match nothing, so the cell would count as hidden."""
    baseline, reform = _households({"S1": 4, "S2": 40, "S3": 80, "S4": 80})
    cells = [
        ("constituencies", "S1", "reform", 2026, "average_change"),
        ("constituencies", "S1", "reform", 2026, "share_gaining"),
        ("ward", "W1", "reform", 2026, "average_change"),
    ]
    prior = PriorPublic(name="seat table", cells=cells)

    with pytest.raises(
        ValueError, match=r"not UK levels: 3, at \['constituencies', 'ward'\]"
    ):
        _compute(baseline, reform, levels=("constituency",), prior_public=[prior])

    # A level given through area_weights is known.
    n = len(baseline["household_id"])
    wards = AreaWeights.from_labels(
        np.asarray(baseline["constituency_code_oa"], dtype=object), np.full(n, 100.0)
    )
    ward = PriorPublic(
        name="ward table", cells=[("ward", "S3", "reform", 2026, "average_change")]
    )
    impact = _compute(
        baseline,
        reform,
        levels=("ward",),
        area_weights={"ward": wards},
        prior_public=[ward],
    )
    assert impact.findings is not None


@pytest.mark.parametrize("blank", ["", "  ", None])
def test_an_empty_region_code_column_falls_back_to_the_stored_region(blank):
    baseline, reform = _households()
    empty = [blank] * len(baseline["region"])
    baseline["region_code_oa"] = reform["region_code_oa"] = empty

    impact = _compute(baseline, reform)

    assert set(impact.public.to_frame()["area_code"]) == {"E12000001", "E12000007"}


def test_a_level_whose_column_gives_no_household_an_area_raises():
    baseline, reform = _households()
    empty = [""] * len(baseline["region"])
    baseline["constituency_code_oa"] = reform["constituency_code_oa"] = empty

    with pytest.raises(ValueError, match="no household an area"):
        _compute(baseline, reform, levels=("constituency",))


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
    regions = ["LONDON"] * len(authorities)
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
    # Regions are keyed on GSS codes, so the engine's names match none.
    names = {"constituency": {"M1": "NORTH_EAST", "M2": "LONDON"}}
    with pytest.raises(DisclosureError, match="not region areas: 2"):
        _compute(baseline, reform, parent_of=names, **options)

    impact = _compute(
        baseline,
        reform,
        parent_of={"constituency": {"M1": "E12000001", "M2": "E12000007"}},
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


def test_a_missing_area_column_names_the_dataset_that_carries_it():
    from policyengine.provenance.manifest import (
        get_release_manifest,
        uk_area_dataset_hint,
    )

    baseline, reform = _households()
    for frame in (baseline, reform):
        del frame["constituency_code_oa"]
    with pytest.raises(ValueError, match="no household an area") as error:
        _compute(baseline, reform, levels=("constituency",))
    hint = uk_area_dataset_hint("constituency")
    if "constituency" in get_release_manifest("uk").region_datasets:
        assert "microcosm_uk_2024_25_dense" in hint
        assert hint in str(error.value)
    else:
        # A national-only cut routes no area regions, so there is no
        # dataset to name.
        assert hint == ""
        assert "certified bundle routes" not in str(error.value)


def test_a_routed_area_names_its_dataset_in_the_error(monkeypatch):
    """Whatever the packaged routing, a routed area's error names its dataset."""
    from policyengine.provenance import manifest

    record = manifest.get_release_manifest("uk")
    data = record.model_dump()
    data["region_datasets"]["constituency"] = {
        "path_template": "microcosm_uk_2024_25_dense.h5"
    }
    data["datasets"]["microcosm_uk_2024_25_dense"] = {
        "path": "microcosm_uk_2024_25_dense.h5",
        "repo_id": "policyengine/populace-uk-private",
        "repo_type": "dataset",
        "revision": "microcosm-uk-2024-25-dense-20261019T000432Z-ee5c2dbe",
    }
    routed = type(record).model_validate(data)
    monkeypatch.setattr(manifest, "get_release_manifest", lambda country: routed)

    baseline, reform = _households()
    for frame in (baseline, reform):
        del frame["constituency_code_oa"]
    with pytest.raises(ValueError, match="no household an area") as error:
        _compute(baseline, reform, levels=("constituency",))
    hint = manifest.uk_area_dataset_hint("constituency")
    assert "'microcosm_uk_2024_25_dense'" in hint
    assert hint in str(error.value)


def test_no_hint_when_nothing_routes_the_area(monkeypatch):
    from policyengine.provenance import manifest

    record = manifest.get_release_manifest("uk")
    unrouted = record.model_copy(
        update={"region_datasets": {"national": record.region_datasets["national"]}}
    )
    monkeypatch.setattr(manifest, "get_release_manifest", lambda country: unrouted)
    assert manifest.uk_area_dataset_hint("constituency") == ""
