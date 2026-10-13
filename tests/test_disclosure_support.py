"""Support counts and the primary rules. Synthetic data."""

import numpy as np
import pytest

from policyengine.disclosure import DisclosureSettings
from policyengine.disclosure.schema import (
    APPROXIMATE,
    BAND_10_TO_29,
    BAND_30_PLUS,
    BAND_UNDER_10,
    PRIVATE_BELOW_FLOOR,
    PRIVATE_DOMINANT,
    PRIVATE_LOW_N_EFF,
    REPORTED,
    WITHHELD,
)
from policyengine.disclosure.support import (
    Support,
    cell_tier,
    family_supports,
    primary_tier,
    support,
    support_band,
)

SETTINGS = DisclosureSettings()
LABELS = {"one_area_per_record": True, "noise": False}


def test_support_counts_clones_of_one_source_once():
    weights = np.full(20, 100.0)
    contributions = np.full(20, 50.0)
    source_index = np.repeat(np.arange(5), 4)

    cell = support(weights, contributions, source_index)

    assert cell.n_sources == 5
    assert cell.n_eff == pytest.approx(5.0)
    assert cell.top_share == pytest.approx(0.2)


def test_support_ignores_records_with_no_change_or_no_weight():
    weights = np.array([100.0, 100.0, 0.0, 100.0])
    contributions = np.array([50.0, 0.0, 50.0, -20.0])
    source_index = np.arange(4)

    cell = support(weights, contributions, source_index)

    assert cell.n_sources == 2
    assert cell.top_share == pytest.approx(50.0 / 70.0)


def test_support_of_nothing_is_empty():
    cell = support(np.ones(3), np.zeros(3), np.arange(3))

    assert cell == Support(0, 0.0, 0.0)


def test_effective_sample_falls_with_unequal_weights():
    weights = np.array([1000.0] + [1.0] * 99)
    cell = support(weights, np.ones(100), np.arange(100))

    assert cell.n_sources == 100
    assert cell.n_eff == pytest.approx((1099.0**2) / (1000.0**2 + 99.0))
    assert cell.n_eff < 2


def test_a_share_has_two_sides():
    weights = np.full(50, 10.0)
    gaining = np.concatenate([np.ones(12), np.zeros(38)])

    gainers, others = family_supports(weights, gaining, np.arange(50), "share_gaining")
    (change,) = family_supports(weights, gaining, np.arange(50), "change")

    assert (gainers.n_sources, others.n_sources) == (12, 38)
    assert change.n_sources == 12


@pytest.mark.parametrize(
    ("n_sources", "tier", "reason"),
    [
        (0, REPORTED, None),
        (9, WITHHELD, PRIVATE_BELOW_FLOOR),
        (10, APPROXIMATE, "thin_support"),
        (29, APPROXIMATE, "thin_support"),
        (30, REPORTED, None),
    ],
)
def test_the_count_floor_and_the_thin_tier_on_label_data(n_sources, tier, reason):
    cell = Support(n_sources, float(n_sources), 0.1)

    assert primary_tier(cell, SETTINGS, **LABELS) == (tier, reason)


def test_effective_sample_withholds_only_on_weight_matrix_data():
    cell = Support(500, 4.0, 0.3)

    on_labels = primary_tier(cell, SETTINGS, one_area_per_record=True, noise=False)
    on_matrix = primary_tier(cell, SETTINGS, one_area_per_record=False, noise=False)

    assert on_labels == (APPROXIMATE, "thin_support")
    assert on_matrix == (WITHHELD, PRIVATE_LOW_N_EFF)


def test_dominance_withholds_only_while_noise_is_off():
    cell = Support(40, 35.0, 0.6)

    without_noise = primary_tier(cell, SETTINGS, one_area_per_record=True, noise=False)
    with_noise = primary_tier(cell, SETTINGS, one_area_per_record=True, noise=True)

    assert without_noise == (WITHHELD, PRIVATE_DOMINANT)
    assert with_noise == (REPORTED, None)


def test_the_count_rule_comes_before_dominance():
    cell = Support(3, 3.0, 0.9)

    assert primary_tier(cell, SETTINGS, **LABELS) == (WITHHELD, PRIVATE_BELOW_FLOOR)


def test_the_floor_can_be_raised_to_thirty():
    settings = DisclosureSettings(min_sources=30)

    tier, _ = primary_tier(Support(20, 20.0, 0.1), settings, **LABELS)

    assert tier == WITHHELD


def test_the_worst_side_of_a_cell_decides():
    passing, thin, small, empty = (
        Support(40, 40.0, 0.1),
        Support(15, 15.0, 0.1),
        Support(4, 4.0, 0.4),
        Support(0, 0.0, 0.0),
    )

    assert cell_tier((passing, empty), SETTINGS, **LABELS) == (REPORTED, None)
    assert cell_tier((passing, thin), SETTINGS, **LABELS)[0] == APPROXIMATE
    assert cell_tier((thin, small), SETTINGS, **LABELS)[0] == WITHHELD


@pytest.mark.parametrize(
    ("n_sources", "band"),
    [(0, BAND_UNDER_10), (9, BAND_UNDER_10), (10, BAND_10_TO_29), (29, BAND_10_TO_29)]
    + [(30, BAND_30_PLUS), (5_000, BAND_30_PLUS)],
)
def test_support_band_never_shows_a_count(n_sources, band):
    cell = Support(n_sources, 1_000.0, 0.1)

    assert support_band(cell, one_area_per_record=True) == band


def test_support_band_uses_the_effective_sample_on_weight_matrix_data():
    cell = Support(5_000, 12.0, 0.1)

    assert support_band(cell, one_area_per_record=False) == BAND_10_TO_29
