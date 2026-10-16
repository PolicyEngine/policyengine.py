"""The release check and the public rows. Synthetic data."""

import stat

import numpy as np
import pandas as pd
import pytest

from policyengine.disclosure import (
    AreaWeights,
    DisclosureError,
    DisclosureSettings,
    PriorPublic,
    Release,
    estimate_change,
)
from policyengine.disclosure.schema import (
    ALREADY_PUBLIC,
    APPROXIMATE,
    AUDIT_COLUMNS,
    NOISE_REFERENCE_PUBLIC,
    PRIVATE_SECONDARY,
    PUBLIC_COLUMNS,
    REASON_DISCLOSURE_CONTROL,
    REASON_THIN_SUPPORT,
    RECOVERABLE_PARENT,
    RECOVERABLE_REMAINDER,
    REPORTED,
    UNCHECKED_OVERLAP,
    WITHHELD,
)

TEST_KEY = "test-key-for-unit-tests-only"
REGION_OF = {"S1": "R1", "S2": "R1", "S3": "R1", "S4": "R2", "S5": "R2", "S6": "R2"}
STRONG = {"S1": 60, "S2": 60, "S3": 60, "S4": 60, "S5": 60, "S6": 60}


def _records(affected, *, households=120, change=200.0, loose=0):
    """Households by seat, with the first ``affected[seat]`` of each changed.

    ``loose`` adds changed households in region R1 that have no seat.
    """
    seats, regions, deltas = [], [], []
    for seat, region in REGION_OF.items():
        seats += [seat] * households
        regions += [region] * households
        deltas += [change] * affected[seat] + [0.0] * (households - affected[seat])
    seats += [""] * loose
    regions += ["R1"] * loose
    deltas += [change] * loose
    n = len(seats)
    baseline = np.random.default_rng(0).uniform(20_000.0, 60_000.0, n)
    return {
        "seats": np.array(seats, dtype=object),
        "regions": np.array(regions, dtype=object),
        "weights": np.full(n, 100.0),
        "source_ids": np.arange(n),
        "baseline": baseline,
        "change": np.array(deltas),
    }


def _estimates(data, level, *, reform="reform", change=None, settings=None, key=None):
    codes = data["seats"] if level == "constituency" else data[f"{level}s"]
    delta = data["change"] if change is None else change
    return estimate_change(
        level=level,
        reform=reform,
        year=2026,
        areas=AreaWeights.from_labels(codes, data["weights"]),
        source_ids=data["source_ids"],
        baseline=data["baseline"],
        reformed=data["baseline"] + delta,
        settings=settings,
        noise_key=key,
    )


def _release(affected, *, loose=0, settings=None, key=None, **options):
    data = _records(affected, loose=loose)
    release = Release(settings, **options)
    release.add(_estimates(data, "region", settings=settings, key=key))
    release.add(_estimates(data, "constituency", settings=settings, key=key))
    release.add_nesting("constituency", "region")
    return release


def _blocking(findings, code):
    return [
        finding for finding in findings if finding.blocking and finding.code == code
    ]


def _public_row(release, area, outcome="average_change", level="constituency"):
    frame = release.to_public().to_frame()
    rows = frame[
        (frame["level"] == level)
        & (frame["area_code"] == area)
        & (frame["outcome"] == outcome)
    ]
    assert len(rows) == 1
    return rows.iloc[0]


def test_to_public_needs_a_check_first():
    release = _release(STRONG)

    with pytest.raises(DisclosureError, match="check"):
        release.to_public()

    assert release.check() == []
    release.to_public()
    release.withhold(
        level="constituency",
        area_code="S1",
        reform="reform",
        year=2026,
        outcome="average_change",
    )
    assert release.findings is None
    with pytest.raises(DisclosureError, match="check"):
        release.to_public()


def test_public_rows_hold_only_public_columns():
    release = _release(STRONG)
    release.check()

    frame = release.to_public().to_frame()

    assert list(frame.columns) == list(PUBLIC_COLUMNS)
    assert not set(frame.columns) & set(AUDIT_COLUMNS)
    assert set(frame["level"]) == {"region", "constituency"}
    assert len(frame) == (2 + 6) * 6
    reported = _public_row(release, "S1")
    assert reported["tier"] == REPORTED
    assert pd.isna(reported["reason"])
    assert reported["lo"] <= reported["value"] <= reported["hi"]


def test_approximate_rows_keep_a_value_and_an_interval():
    release = _release({**STRONG, "S1": 14})
    release.check()

    row = _public_row(release, "S1")

    assert (row["tier"], row["reason"]) == (APPROXIMATE, REASON_THIN_SUPPORT)
    assert row["lo"] <= row["value"] <= row["hi"]
    assert row["direction"] == "gain"


def test_one_withheld_seat_in_a_region_is_recoverable_until_a_second_goes():
    release = _release({**STRONG, "S1": 4, "S2": 30})

    findings = release.check()

    blocking = _blocking(findings, RECOVERABLE_REMAINDER)
    assert {finding.family for finding in blocking} == {"change", "share_gaining"}
    for finding in blocking:
        assert (finding.relation, finding.group) == ("nesting", "R1")
        assert finding.members == ["S1"]
        assert finding.suggested == "S2"
    with pytest.raises(DisclosureError, match="recoverable_remainder"):
        release.to_public()

    for outcome in ("average_change", "share_gaining"):
        release.withhold(
            level="constituency",
            area_code="S2",
            reform="reform",
            year=2026,
            outcome=outcome,
        )
    assert release.check() == []
    for seat in ("S1", "S2"):
        row = _public_row(release, seat)
        assert (row["tier"], row["reason"]) == (WITHHELD, REASON_DISCLOSURE_CONTROL)
        for column in ("value", "lo", "hi", "direction", "support_band"):
            assert pd.isna(row[column])
    assert _public_row(release, "S3")["tier"] == REPORTED
    assert _public_row(release, "S2", "share_no_change")["tier"] == WITHHELD
    assert _public_row(release, "S2", "share_losing")["tier"] == REPORTED


def test_findings_hold_labels_and_never_counts():
    release = _release({**STRONG, "S1": 4, "S2": 30})

    for finding in release.check():
        assert not any(
            character.isdigit() for character in finding.message.replace("R1", "")
        )


def test_withheld_seats_that_pass_together_need_no_more_withholding():
    release = _release({**STRONG, "S1": 6, "S2": 7})

    findings = release.check()

    assert _blocking(findings, RECOVERABLE_REMAINDER) == []
    assert _public_row(release, "S1")["tier"] == WITHHELD
    assert _public_row(release, "S2")["tier"] == WITHHELD
    assert _public_row(release, "S3")["tier"] == REPORTED


def test_a_withheld_parent_gives_no_total_to_subtract_from():
    release = _release({**STRONG, "S1": 4, "S2": 0, "S3": 0})

    assert release.check() == []
    assert _public_row(release, "R1", level="region")["tier"] == WITHHELD
    assert _public_row(release, "S1")["tier"] == WITHHELD
    assert _public_row(release, "S2")["value"] == 0.0


def test_the_suggestion_skips_cells_that_add_nothing():
    release = _release({**STRONG, "S1": 4, "S2": 0, "S3": 60})

    findings = _blocking(release.check(), RECOVERABLE_REMAINDER)

    assert {finding.suggested for finding in findings} == {"S3"}
    assert {finding.group_level for finding in findings} == {"region"}


def test_noise_does_not_lift_the_count_floor_for_a_remainder():
    settings = DisclosureSettings(noise=True)
    release = _release({**STRONG, "S1": 4}, settings=settings, key=TEST_KEY)

    assert _blocking(release.check(), RECOVERABLE_REMAINDER)


def test_records_with_no_seat_are_part_of_the_remainder():
    release = _release(STRONG, loose=5)

    findings = _blocking(release.check(), RECOVERABLE_REMAINDER)

    assert {finding.group for finding in findings} == {"R1"}
    assert all(finding.members == [] for finding in findings)


def test_a_withheld_parent_with_all_children_published_is_recoverable():
    release = _release(STRONG)
    release.withhold(
        level="region",
        area_code="R1",
        reform="reform",
        year=2026,
        outcome="average_change",
    )

    findings = _blocking(release.check(), RECOVERABLE_PARENT)

    assert [(f.relation, f.group, f.family) for f in findings] == [
        ("nesting", "R1", "change")
    ]


def test_a_reference_level_is_checked_against_but_not_published():
    data = _records({**STRONG, "S1": 4})
    release = Release()
    release.add(_estimates(data, "region"), publish=False)
    release.add(_estimates(data, "constituency"))
    release.add_nesting("constituency", "region")

    assert _blocking(release.check(), RECOVERABLE_REMAINDER)
    release.withhold(
        level="constituency",
        area_code="S2",
        reform="reform",
        year=2026,
        outcome="average_change",
    )
    release.withhold(
        level="constituency",
        area_code="S2",
        reform="reform",
        year=2026,
        outcome="share_gaining",
    )
    release.check()
    assert set(release.to_public().to_frame()["level"]) == {"constituency"}


def _package_release(reference=()):
    data = _records(STRONG)
    seat_one = data["seats"] == "S1"
    broad = data["change"]
    narrow = np.where(seat_one & (np.arange(len(seat_one)) % 120 < 4), 500.0, 0.0)
    narrow = np.where(~seat_one & (np.arange(len(seat_one)) % 120 < 60), 500.0, narrow)
    release = Release()
    for reform, change in (("A", broad), ("B", narrow), ("P", broad + narrow)):
        release.add(
            _estimates(data, "constituency", reform=reform, change=change),
            publish=reform not in reference,
        )
    release.add_package("P", ["A", "B"])
    return release


def test_a_package_gives_away_a_withheld_component():
    release = _package_release()

    findings = _blocking(release.check(), RECOVERABLE_REMAINDER)

    assert [(f.relation, f.reform, f.group, f.members) for f in findings] == [
        ("package", "P", "S1", ["B"])
    ]
    assert findings[0].suggested == "A"

    release.withhold(
        level="constituency",
        area_code="S1",
        reform="P",
        year=2026,
        outcome="average_change",
    )
    assert release.check() == []


def test_a_withheld_reference_component_is_hidden_too():
    """Public elsewhere means public where it passes; the rest is secret."""
    release = _package_release(reference=("B",))

    findings = _blocking(release.check(), RECOVERABLE_REMAINDER)

    assert [(f.relation, f.group, f.members, f.suggested) for f in findings] == [
        ("package", "S1", ["B"], "A")
    ]


def test_a_relation_between_references_only_is_not_checked():
    assert _package_release(reference=("A", "B", "P")).check() == []


def test_withheld_cells_of_a_reference_child_level_are_hidden_too():
    data = _records({**STRONG, "S1": 4})
    release = Release()
    release.add(_estimates(data, "region"))
    release.add(_estimates(data, "constituency"), publish=False)
    release.add_nesting("constituency", "region")

    findings = _blocking(release.check(), RECOVERABLE_REMAINDER)

    assert {(f.group, tuple(f.members), f.suggested) for f in findings} == {
        ("R1", ("S1",), None)
    }
    # The seats are public elsewhere, so the fix is on the published side.
    for finding in findings:
        release.withhold(
            level=finding.group_level,
            area_code=finding.group,
            reform="reform",
            year=2026,
            outcome="average_change" if finding.family == "change" else finding.family,
        )
    assert release.check() == []
    assert set(release.to_public().to_frame()["level"]) == {"region"}


def test_a_withheld_package_with_all_components_published_is_recoverable():
    release = _package_release()
    for reform in ("A", "P"):
        release.withhold(
            level="constituency",
            area_code="S4",
            reform=reform,
            year=2026,
            outcome="average_change",
        )
    release.withhold(
        level="constituency",
        area_code="S1",
        reform="P",
        year=2026,
        outcome="average_change",
    )
    assert release.check() == []

    release = _package_release()
    release.withhold(
        level="constituency",
        area_code="S4",
        reform="P",
        year=2026,
        outcome="average_change",
    )
    findings = _blocking(release.check(), RECOVERABLE_PARENT)
    assert [(f.relation, f.group) for f in findings] == [("package", "S4")]


def test_relations_need_their_estimates_on_the_same_records():
    data = _records(STRONG)
    release = Release()
    release.add(_estimates(data, "constituency"))
    release.add_nesting("constituency", "region")
    with pytest.raises(DisclosureError, match="needs region estimates"):
        release.check()

    other = _records(STRONG, loose=3)
    release.add(_estimates(other, "region"))
    with pytest.raises(DisclosureError, match="same records"):
        release.check()

    release = Release()
    release.add(_estimates(data, "constituency", reform="P"))
    release.add_package("P", ["A"])
    with pytest.raises(DisclosureError, match="component"):
        release.check()


def test_a_seat_in_two_regions_is_not_a_nesting():
    data = _records(STRONG)
    data["regions"][0] = "R2"
    release = Release()
    release.add(_estimates(data, "region"))
    release.add(_estimates(data, "constituency"))
    release.add_nesting("constituency", "region")

    with pytest.raises(DisclosureError, match="more than one"):
        release.check()


def test_levels_published_together_need_a_declared_relation():
    data = _records(STRONG)
    data["local_authoritys"] = np.where(data["seats"] < "S3", "L1", "L2").astype(object)

    def build(**options):
        release = Release(**options)
        release.add(_estimates(data, "constituency"))
        release.add(_estimates(data, "local_authority"))
        return release

    blocked = build()
    findings = blocked.check()
    assert [(f.code, f.blocking, f.level) for f in findings] == [
        (UNCHECKED_OVERLAP, True, "constituency|local_authority")
    ]
    with pytest.raises(DisclosureError, match=UNCHECKED_OVERLAP):
        blocked.to_public()

    accepted = build(acknowledge=[UNCHECKED_OVERLAP])
    assert [f.blocking for f in accepted.check()] == [False]
    accepted.to_public()

    with pytest.raises(ValueError, match="cannot be acknowledged"):
        Release(acknowledge=[RECOVERABLE_REMAINDER])


def _withhold_suggestions(release, rounds=20):
    """Resolve blocking findings one at a time, as a person would."""
    withheld = set()
    for _ in range(rounds):
        blocking = [finding for finding in release.check() if finding.blocking]
        if not blocking:
            return withheld
        finding = blocking[0]
        level = finding.level if finding.suggested else finding.group_level
        area = finding.suggested or finding.group
        withheld.add((level, area))
        family = finding.family
        release.withhold(
            level=level,
            area_code=area,
            reform="reform",
            year=2026,
            outcome="average_change" if family == "change" else family,
        )
    raise AssertionError("findings did not resolve")


def test_an_area_minus_the_public_areas_inside_it_is_checked():
    """A local authority that is one seat plus a few households of another."""
    data = _records(STRONG)
    authorities = np.where(data["seats"] == "S1", "L1", "L2").astype(object)
    authorities[np.flatnonzero(data["seats"] == "S2")[:5]] = "L1"
    data["local_authoritys"] = authorities
    release = Release(acknowledge=[UNCHECKED_OVERLAP])
    release.add(_estimates(data, "constituency"))
    release.add(_estimates(data, "local_authority"))

    findings = release.check()

    blocking = _blocking(findings, RECOVERABLE_REMAINDER)
    # The five households are recovered three ways: L1 minus S1, S1's
    # authorities minus S1, and S2 to S6 minus L2.
    assert {
        (f.relation, f.level, f.group, f.group_level, f.suggested) for f in blocking
    } == {
        ("containment", "constituency", "L1", "local_authority", "S1"),
        ("containment", "local_authority", "S1", "constituency", "L1"),
        ("containment", "constituency", "L2", "local_authority", "S2"),
    }
    # Also the share losing: "none of these five lose" is a statement about five.
    assert {f.family for f in blocking} == {"change", "share_gaining", "share_losing"}
    overlap = [f for f in findings if f.code == UNCHECKED_OVERLAP]
    assert [f.blocking for f in overlap] == [False]
    assert "wholly inside" in overlap[0].message
    with pytest.raises(DisclosureError, match=RECOVERABLE_REMAINDER):
        release.to_public()

    withheld = _withhold_suggestions(release)

    # Two cells must go: one that breaks L1 minus S1, one that breaks the
    # seats around L2.
    assert len(withheld) == 2
    assert ("constituency", "S2") in withheld
    release.to_public()


def test_an_area_covered_by_the_areas_that_meet_it_is_checked():
    """Two seats that cover an authority, each with a few households outside it."""
    seats = ["S1"] * 200 + ["S2"] * 200 + ["S3"] * 200 + ["S4"] * 200
    authorities = (
        ["L1"] * 197
        + ["L2"] * 3
        + ["L1"] * 198
        + ["L2"] * 2
        + ["L2"] * 100
        + ["L3"] * 100
        + ["L2"] * 100
        + ["L3"] * 100
    )
    n = len(seats)
    baseline = np.random.default_rng(1).uniform(20_000.0, 60_000.0, n)
    data = {
        "seats": np.array(seats, dtype=object),
        "local_authoritys": np.array(authorities, dtype=object),
        "weights": np.full(n, 100.0),
        "source_ids": np.arange(n),
        "baseline": baseline,
        "change": np.full(n, 200.0),
    }
    release = Release(acknowledge=[UNCHECKED_OVERLAP])
    release.add(_estimates(data, "constituency"))
    release.add(_estimates(data, "local_authority"))

    blocking = _blocking(release.check(), RECOVERABLE_REMAINDER)

    # No area of either level lies wholly inside an area of the other, yet
    # S1 + S2 - L1 gives the five households that the two seats hold in L2.
    assert {(f.level, f.group, f.group_level) for f in blocking} == {
        ("constituency", "L1", "local_authority")
    }
    assert {f.suggested for f in blocking} <= {"S1", "S2"}
    _withhold_suggestions(release)
    release.to_public()


def test_public_areas_inside_a_withheld_area_cannot_add_up_to_it():
    data = _records(STRONG)
    data["local_authoritys"] = np.where(
        np.isin(data["seats"], ["S1", "S2"]), "L1", "L2"
    ).astype(object)
    release = Release(acknowledge=[UNCHECKED_OVERLAP])
    release.add(_estimates(data, "constituency"))
    release.add(_estimates(data, "local_authority"))
    release.withhold(
        level="local_authority",
        area_code="L1",
        reform="reform",
        year=2026,
        outcome="average_change",
    )

    findings = _blocking(release.check(), RECOVERABLE_PARENT)

    assert [(f.relation, f.group, f.group_level, f.family) for f in findings] == [
        ("containment", "L1", "local_authority", "change")
    ]


def test_a_cell_that_is_already_public_is_not_a_secret():
    cells = [
        ("constituency", "S1", "reform", 2026, "average_change"),
        ("constituency", "S1", "reform", 2026, "share_gaining"),
    ]
    release = _release(
        {**STRONG, "S1": 4}, prior_public=[PriorPublic(name="2025 table", cells=cells)]
    )

    findings = release.check()

    assert not any(finding.blocking for finding in findings)
    assert {(f.code, f.group, tuple(f.members)) for f in findings} == {
        (ALREADY_PUBLIC, "2025 table", ("S1",))
    }
    assert _public_row(release, "S1")["tier"] == WITHHELD


def test_a_prior_with_another_noise_setting_blocks_until_acknowledged():
    cells = [("constituency", "S3", "reform", 2026, "average_change")]
    prior = PriorPublic(name="noised table", noise=True, cells=cells)

    blocked = _release(STRONG, prior_public=[prior])
    findings = blocked.check()
    assert [(f.code, f.blocking, f.members) for f in findings] == [
        (NOISE_REFERENCE_PUBLIC, True, ["S3"])
    ]

    accepted = _release(
        STRONG, prior_public=[prior], acknowledge=[NOISE_REFERENCE_PUBLIC]
    )
    assert [f.blocking for f in accepted.check()] == [False]


@pytest.mark.parametrize(
    "order", [("region", "constituency"), ("constituency", "region")]
)
def test_a_prior_cell_must_name_an_area_of_a_level_the_release_holds(order):
    """Regions published under other codes would still count as hidden."""
    prior = PriorPublic(
        name="regional table",
        cells=[
            ("region", "North", "reform", 2026, "average_change"),
            ("region", "North", "reform", 2026, "share_gaining"),
            ("region", "R2", "reform", 2026, "average_change"),
        ],
    )
    data = _records(STRONG)
    release = Release(prior_public=[prior])
    for level in order:
        # The regions are a reference, as in a seat release after a regional one.
        release.add(_estimates(data, level), publish=level == "constituency")
    release.add_nesting("constituency", "region")

    with pytest.raises(
        DisclosureError, match=r"'regional table' that name no region area.*: 2\."
    ) as raised:
        release.check()
    assert "North" not in str(raised.value)


def test_a_prior_cell_needs_a_known_outcome():
    cells = [("constituency", "S1", "reform", 2026, "avg_change")]

    with pytest.raises(DisclosureError, match="'typo table' whose outcome is unknown"):
        Release(prior_public=[PriorPublic(name="typo table", cells=cells)])


def test_prior_cells_of_other_publications_are_allowed():
    """Cells for other reforms, years or levels take no part in the check."""
    cells = [
        ("constituency", "S1", "other reform", 2026, "average_change"),
        ("constituency", "S1", "reform", 2025, "share_gaining"),
        ("region", "R1", "reform", 2027, "share_no_change"),
        ("local_authority", "L9", "reform", 2026, "average_change"),
    ]
    prior = PriorPublic(name="other tables", cells=cells)
    affected = {**STRONG, "S1": 4, "S2": 30}

    findings = _release(affected, prior_public=[prior]).check()

    assert findings == _release(affected).check()
    assert _blocking(findings, RECOVERABLE_REMAINDER)


def test_a_weight_matrix_child_needs_parent_of_under_several_parents():
    data = _records(STRONG)
    n = len(data["seats"])
    matrix = np.ones((2, n))
    seats = estimate_change(
        level="constituency",
        reform="reform",
        year=2026,
        areas=AreaWeights.from_matrix(matrix, ["M1", "M2"]),
        source_ids=data["source_ids"],
        baseline=data["baseline"],
        reformed=data["baseline"] + data["change"],
    )

    release = Release()
    release.add(_estimates(data, "region"))
    release.add(seats)
    release.add_nesting("constituency", "region")
    with pytest.raises(DisclosureError, match="parent_of"):
        release.check()

    release = Release()
    release.add(_estimates(data, "region"))
    release.add(seats)
    release.add_nesting("constituency", "region", {"M1": "R1", "M2": "R2"})
    assert release.check() == []


def _seat_matrix_release(parent_of):
    """400 records in two regions and a 4 x 400 seat matrix.

    Three records carry seat M1, so it is withheld. M2 holds the rest of R1;
    M3 and M4 share R2, and a few records there carry weight in both.
    """
    n = 400
    regions = np.array(["R1"] * 200 + ["R2"] * 200, dtype=object)
    matrix = np.zeros((4, n))
    matrix[0, :3] = 100.0
    matrix[1, 3:200] = 100.0
    matrix[2, 200:300] = 100.0
    matrix[3, 300:] = 100.0
    matrix[2:, 290:300] = 50.0
    baseline = np.random.default_rng(2).uniform(20_000.0, 60_000.0, n)
    common = {
        "reform": "reform",
        "year": 2026,
        "source_ids": np.arange(n),
        "baseline": baseline,
        "reformed": baseline + 200.0,
    }
    release = Release()
    release.add(
        estimate_change(
            level="region",
            areas=AreaWeights.from_labels(regions, np.full(n, 100.0)),
            **common,
        )
    )
    release.add(
        estimate_change(
            level="constituency",
            areas=AreaWeights.from_matrix(matrix, ["M1", "M2", "M3", "M4"]),
            **common,
        )
    )
    release.add_nesting("constituency", "region", parent_of)
    return release


def test_parent_of_must_name_areas_of_the_parent_level():
    """Regions named another way left every group empty, so nothing was found."""
    own = {"M1": "R1", "M2": "R1", "M3": "R2", "M4": "R2"}

    findings = _seat_matrix_release(own).check()

    blocking = _blocking(findings, RECOVERABLE_REMAINDER)
    assert len(blocking) == len(findings) == 3
    assert {f.family for f in blocking} == {"change", "share_gaining", "share_losing"}
    assert {(f.relation, f.group, tuple(f.members)) for f in blocking} == {
        ("nesting", "R1", ("M1",))
    }

    renamed = {"M1": "North", "M2": "North", "M3": "South", "M4": "South"}
    with pytest.raises(DisclosureError, match="not region areas: 2") as raised:
        _seat_matrix_release(renamed).check()
    assert "North" not in str(raised.value)
    assert "South" not in str(raised.value)

    with pytest.raises(DisclosureError, match="not region areas: 1"):
        _seat_matrix_release({**own, "M4": "South"}).check()


def test_the_release_refuses_mixed_settings_and_duplicates():
    data = _records(STRONG)
    release = Release()
    release.add(_estimates(data, "constituency"))

    with pytest.raises(DisclosureError, match="already holds"):
        release.add(_estimates(data, "constituency"))
    with pytest.raises(DisclosureError, match="other settings"):
        release.add(
            _estimates(data, "region", settings=DisclosureSettings(min_sources=30))
        )


def test_withhold_takes_a_cell_of_the_release_and_a_family_outcome():
    release = _release(STRONG)
    cell = {"level": "constituency", "reform": "reform", "year": 2026}

    with pytest.raises(ValueError, match="share_gaining"):
        release.withhold(area_code="S1", outcome="share_no_change", **cell)
    with pytest.raises(DisclosureError, match="no cell"):
        release.withhold(area_code="S9", outcome="average_change", **cell)


def test_the_audit_is_private_and_stays_out_of_repositories(tmp_path):
    release = _release({**STRONG, "S1": 4})
    release.withhold(
        level="constituency",
        area_code="S2",
        reform="reform",
        year=2026,
        outcome="average_change",
    )
    repository = tmp_path / "repo"
    (repository / ".git").mkdir(parents=True)

    with pytest.raises(DisclosureError, match="git repository"):
        release.write_audit(repository / "private" / "audit")

    path = release.write_audit(tmp_path / "private")
    audit = pd.read_csv(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert set(AUDIT_COLUMNS) <= set(audit.columns)
    manual = audit[
        (audit["area_code"] == "S2") & (audit["outcome"] == "average_change")
    ].iloc[0]
    assert (manual["tier"], manual["private_reason"]) == (WITHHELD, PRIVATE_SECONDARY)
    assert not list(repository.rglob("*.csv"))
