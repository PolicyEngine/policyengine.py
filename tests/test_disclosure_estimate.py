"""Private estimates: values, support, intervals and rounding. Synthetic data."""

import copy
import math
import pickle

import numpy as np
import pandas as pd
import pytest

from policyengine.disclosure import (
    NOISE_KEY_ENV,
    AreaWeights,
    DisclosureKeyError,
    DisclosureSettings,
    Release,
    estimate_change,
    validate_public,
)
from policyengine.disclosure import estimate as estimate_module
from policyengine.disclosure.schema import (
    APPROXIMATE,
    BAND_30_PLUS,
    BAND_UNDER_10,
    PRIVATE_BELOW_FLOOR,
    PRIVATE_DOMINANT,
    PRIVATE_LOW_N_EFF,
    PRIVATE_SHARE_SPLIT,
    PRIVATE_UNDEFINED,
    REPORTED,
    WITHHELD,
)
from policyengine.outputs.uk_geography_impact import (
    compute_longwise_uk_geography_impacts,
)

TEST_KEY = "test-key-for-unit-tests-only"


def _population(spec, *, clones=1, weight=100.0, change=200.0, seed=0):
    """Build records from ``{area: (households, affected)}``.

    Each household is its own survey household unless ``clones`` is above 1,
    in which case each survey household appears that many times in the area.
    """
    rng = np.random.default_rng(seed)
    codes, deltas = [], []
    for code, (households, affected) in spec.items():
        codes += [code] * households
        deltas += [change] * affected + [0.0] * (households - affected)
    n = len(codes)
    baseline = rng.uniform(20_000.0, 60_000.0, n)
    return {
        "codes": np.array(codes, dtype=object),
        "weights": np.full(n, weight),
        "source_ids": np.arange(n) // clones,
        "baseline": baseline,
        "reformed": baseline + np.array(deltas),
    }


def _estimate(data, *, settings=None, noise_key=None, areas=None):
    return estimate_change(
        level="constituency",
        reform="reform",
        year=2026,
        areas=areas or AreaWeights.from_labels(data["codes"], data["weights"]),
        source_ids=data["source_ids"],
        baseline=data["baseline"],
        reformed=data["reformed"],
        settings=settings,
        noise_key=noise_key,
    )


def _cell(estimates, area, outcome):
    table = estimates._table
    rows = table[(table["area_code"] == area) & (table["outcome"] == outcome)]
    assert len(rows) == 1
    return rows.iloc[0]


def test_exact_values_match_the_unprotected_computation():
    rng = np.random.default_rng(3)
    n = 240
    codes = np.repeat(np.array(["A", "B", "C"], dtype=object), 80)
    weights = rng.uniform(50.0, 400.0, n)
    baseline = rng.uniform(15_000.0, 80_000.0, n)
    change = np.where(rng.random(n) < 0.5, rng.choice([-300.0, 250.0, 900.0], n), 0.0)
    data = {
        "codes": codes,
        "weights": weights,
        "source_ids": np.arange(n),
        "baseline": baseline,
        "reformed": baseline + change,
    }

    estimates = _estimate(data)
    household = pd.DataFrame(
        {"code": codes, "household_weight": weights, "household_net_income": baseline}
    )
    expected = compute_longwise_uk_geography_impacts(
        baseline_household=household,
        reform_household=household.assign(household_net_income=baseline + change),
        geography_column="code",
        result_key_prefix="area",
    )

    for row in expected:
        average = _cell(estimates, row["area_code"], "average_change")
        relative = _cell(estimates, row["area_code"], "relative_change")
        total = _cell(estimates, row["area_code"], "total_change")
        assert average["exact_value"] == pytest.approx(
            row["average_household_income_change"]
        )
        assert relative["exact_value"] == pytest.approx(
            row["relative_household_income_change"]
        )
        assert total["exact_value"] == pytest.approx(
            row["average_household_income_change"] * row["population"]
        )


def test_the_floor_withholds_under_ten_contributing_households():
    estimates = _estimate(_population({"A": (100, 9), "B": (100, 10)}))

    below = _cell(estimates, "A", "average_change")
    at_floor = _cell(estimates, "B", "average_change")

    assert (below["tier"], below["private_reason"]) == (WITHHELD, PRIVATE_BELOW_FLOOR)
    assert below["support_band"] == BAND_UNDER_10
    assert at_floor["tier"] == APPROXIMATE
    assert at_floor["n_sources"] == 10


def test_clones_of_one_survey_household_count_once():
    estimates = _estimate(_population({"A": (40, 40)}, clones=8))

    cell = _cell(estimates, "A", "average_change")

    assert cell["n_sources"] == 5
    assert cell["tier"] == WITHHELD


def test_outcomes_with_one_numerator_share_a_tier():
    estimates = _estimate(_population({"A": (100, 9), "B": (100, 60)}))

    for area in ("A", "B"):
        tiers = {
            _cell(estimates, area, outcome)["tier"]
            for outcome in ("average_change", "relative_change", "total_change")
        }
        assert len(tiers) == 1


def test_a_cell_with_no_contributing_household_publishes_zero():
    estimates = _estimate(_population({"A": (50, 0), "B": (100, 60)}))

    cell = _cell(estimates, "A", "average_change")
    losing = _cell(estimates, "B", "share_losing")

    assert (cell["value"], cell["lo"], cell["hi"]) == (0.0, 0.0, 0.0)
    assert (cell["tier"], cell["direction"]) == (REPORTED, "no_change")
    # A zero rests on the households that did not change, as a zero share
    # rests on its other side.
    assert cell["n_sources"] == 0
    assert cell["support_band"] == BAND_30_PLUS
    assert (losing["value"], losing["tier"]) == (0.0, REPORTED)
    assert losing["support_band"] == BAND_30_PLUS


def test_changes_inside_the_tolerance_count_as_no_change():
    data = _population({"A": (100, 60)}, change=0.5)

    cell = _cell(_estimate(data), "A", "average_change")

    assert cell["n_sources"] == 0
    assert cell["exact_value"] == 0.0


def test_thin_support_is_approximate_and_strong_support_is_reported():
    estimates = _estimate(_population({"A": (200, 12), "B": (200, 90)}))

    assert _cell(estimates, "A", "average_change")["tier"] == APPROXIMATE
    assert _cell(estimates, "B", "average_change")["tier"] == REPORTED
    assert _cell(estimates, "B", "average_change")["support_band"] == BAND_30_PLUS


def test_a_heavy_contributor_is_withheld_only_while_noise_is_off():
    data = _population({"A": (60, 60)})
    data["reformed"][0] += 500_000.0

    without_noise = _cell(_estimate(data), "A", "average_change")
    with_noise = _cell(
        _estimate(data, settings=DisclosureSettings(noise=True), noise_key=TEST_KEY),
        "A",
        "average_change",
    )

    assert without_noise["top_share"] > 0.5
    assert (without_noise["tier"], without_noise["private_reason"]) == (
        WITHHELD,
        PRIVATE_DOMINANT,
    )
    assert with_noise["tier"] == REPORTED


def test_one_heavy_record_in_many_areas_fails_the_effective_sample_gate():
    """A distinct-count floor passes this cell; the n_eff gate must not."""
    n = 300
    matrix = np.ones((3, n))
    matrix[:, 0] = 1_000_000.0
    data = _population({"X": (n, n)})
    areas = AreaWeights.from_matrix(matrix, ["a", "b", "c"])

    estimates = _estimate(data, areas=areas)

    for area in ("a", "b", "c"):
        cell = _cell(estimates, area, "average_change")
        assert cell["n_sources"] == n
        assert cell["n_eff"] < 2
        assert (cell["tier"], cell["private_reason"]) == (WITHHELD, PRIVATE_LOW_N_EFF)
        assert cell["support_band"] == BAND_UNDER_10


def test_one_row_of_a_weight_matrix_keeps_the_effective_sample_gate():
    """A per-seat slice of a dense matrix has one weight per record."""
    n = 50
    weights = np.array([10_000.0] * 3 + [1.0] * 47)
    data = _population({"a": (n, n)})
    data["weights"] = weights

    as_matrix = _estimate(data, areas=AreaWeights.from_matrix(weights[None, :], ["a"]))
    as_labels = _estimate(data)

    matrix_cell = _cell(as_matrix, "a", "average_change")
    label_cell = _cell(as_labels, "a", "average_change")
    assert matrix_cell["n_eff"] == pytest.approx(label_cell["n_eff"])
    assert matrix_cell["n_eff"] < 10
    assert (matrix_cell["tier"], matrix_cell["private_reason"]) == (
        WITHHELD,
        PRIVATE_LOW_N_EFF,
    )
    assert matrix_cell["support_band"] == BAND_UNDER_10
    assert label_cell["tier"] == APPROXIMATE
    assert label_cell["support_band"] == BAND_30_PLUS


def test_an_even_weight_matrix_passes_and_bands_by_effective_sample():
    n = 300
    data = _population({"X": (n, n)})
    areas = AreaWeights.from_matrix(np.ones((2, n)), ["a", "b"])

    cell = _cell(_estimate(data, areas=areas), "a", "average_change")

    assert cell["tier"] == REPORTED
    assert cell["support_band"] == BAND_30_PLUS


def test_noise_changes_the_change_but_never_a_denominator():
    data = _population({"A": (400, 300), "B": (400, 200)}, seed=5)
    data["reformed"] += np.where(data["reformed"] > data["baseline"], 150.0, 0.0)
    plain = _estimate(data)
    noised = _estimate(
        data, settings=DisclosureSettings(noise=True), noise_key=TEST_KEY
    )

    for area in ("A", "B"):
        plain_total = _cell(plain, area, "total_change")["exact_value"]
        noised_total = _cell(noised, area, "total_change")["exact_value"]
        assert noised_total != plain_total
        assert 0.88 <= noised_total / plain_total <= 1.12
        for outcome in ("average_change", "relative_change"):
            plain_denominator = plain_total / _cell(plain, area, outcome)["exact_value"]
            noised_denominator = (
                noised_total / _cell(noised, area, outcome)["exact_value"]
            )
            assert noised_denominator == pytest.approx(plain_denominator)


def test_noise_is_about_a_tenth_of_the_sampling_error_of_a_total():
    rng = np.random.default_rng(11)
    data = _population({"A": (2_000, 2_000)})
    data["reformed"] = data["baseline"] + rng.uniform(100.0, 900.0, 2_000)
    plain = _cell(_estimate(data), "A", "total_change")
    noised = _cell(
        _estimate(data, settings=DisclosureSettings(noise=True), noise_key=TEST_KEY),
        "A",
        "total_change",
    )

    shift = (noised["exact_value"] - plain["exact_value"]) / plain["standard_error"]

    assert abs(shift) < 0.4
    assert noised["standard_error"] / plain["standard_error"] == pytest.approx(
        1.0, abs=0.05
    )


def test_noise_without_a_key_fails_before_anything_is_computed(monkeypatch):
    monkeypatch.delenv(NOISE_KEY_ENV, raising=False)
    data = _population({"A": (50, 30)})
    data["baseline"] = data["baseline"][:10]

    with pytest.raises(DisclosureKeyError):
        _estimate(data, settings=DisclosureSettings(noise=True))


def test_noise_reads_the_key_from_the_environment(monkeypatch):
    monkeypatch.setenv(NOISE_KEY_ENV, TEST_KEY)
    data = _population({"A": (80, 60)})
    settings = DisclosureSettings(noise=True)

    from_environment = _estimate(data, settings=settings)
    from_argument = _estimate(data, settings=settings, noise_key=TEST_KEY)

    assert from_environment.noise
    pd.testing.assert_frame_equal(from_environment._table, from_argument._table)


def test_shares_stay_between_zero_and_one_under_noise():
    data = _population({"A": (80, 80)})

    estimates = _estimate(
        data, settings=DisclosureSettings(noise=True), noise_key=TEST_KEY
    )

    gaining = _cell(estimates, "A", "share_gaining")
    unchanged = _cell(estimates, "A", "share_no_change")
    assert 0.0 <= gaining["exact_value"] <= 1.0
    assert 0.0 <= gaining["lo"] <= gaining["value"] <= gaining["hi"] <= 1.0
    assert unchanged["exact_value"] >= 0.0


def test_published_shares_add_to_one():
    rng = np.random.default_rng(8)
    n = 600
    baseline = rng.uniform(20_000.0, 50_000.0, n)
    data = {
        "codes": np.repeat(np.array(["A", "B"], dtype=object), n // 2),
        "weights": rng.uniform(80.0, 300.0, n),
        "source_ids": np.arange(n),
        "baseline": baseline,
        "reformed": baseline + rng.choice([-400.0, 0.0, 300.0], n),
    }

    estimates = _estimate(data)

    for area in ("A", "B"):
        parts = [
            _cell(estimates, area, outcome)
            for outcome in ("share_gaining", "share_losing", "share_no_change")
        ]
        assert all(part["tier"] != WITHHELD for part in parts)
        assert sum(part["value"] for part in parts) == pytest.approx(1.0, abs=1e-12)
        assert sum(part["exact_value"] for part in parts) == pytest.approx(1.0)


def test_published_shares_add_to_one_when_their_rounding_differs():
    """A common share and a rare one round on different bases."""
    n = 1_000
    baseline = np.full(n, 30_000.0)
    change = np.array([300.0] * 500 + [-300.0] * 20 + [0.0] * 480)
    data = {
        "codes": np.full(n, "A", dtype=object),
        "weights": np.random.default_rng(9).uniform(80.0, 300.0, n),
        "source_ids": np.arange(n),
        "baseline": baseline,
        "reformed": baseline + change,
    }

    estimates = _estimate(data)

    gaining = _cell(estimates, "A", "share_gaining")
    losing = _cell(estimates, "A", "share_losing")
    unchanged = _cell(estimates, "A", "share_no_change")
    assert gaining["rounding_base"] > losing["rounding_base"]
    assert unchanged["tier"] != WITHHELD
    assert gaining["value"] + losing["value"] + unchanged["value"] == pytest.approx(
        1.0, abs=1e-12
    )
    assert unchanged["lo"] <= unchanged["value"] <= unchanged["hi"]
    release = Release()
    release.add(estimates)
    release.check()
    assert validate_public(release.to_public()) == []


def test_a_share_needs_both_sides_above_the_floor():
    estimates = _estimate(_population({"A": (100, 95), "B": (100, 50)}))

    few_others = _cell(estimates, "A", "share_gaining")
    balanced = _cell(estimates, "B", "share_gaining")

    assert few_others["tier"] == WITHHELD
    assert balanced["tier"] != WITHHELD


def test_two_shares_are_not_published_when_they_give_a_small_third():
    baseline = np.full(83, 30_000.0)
    change = np.array([300.0] * 40 + [-300.0] * 40 + [0.0] * 3)
    data = {
        "codes": np.full(83, "A", dtype=object),
        "weights": np.full(83, 100.0),
        "source_ids": np.arange(83),
        "baseline": baseline,
        "reformed": baseline + change,
    }

    estimates = _estimate(data)

    gaining = _cell(estimates, "A", "share_gaining")
    losing = _cell(estimates, "A", "share_losing")
    unchanged = _cell(estimates, "A", "share_no_change")
    assert gaining["tier"] != WITHHELD
    assert (losing["tier"], losing["private_reason"]) == (WITHHELD, PRIVATE_SHARE_SPLIT)
    assert unchanged["tier"] == WITHHELD


def test_a_uniform_change_has_no_sampling_error_in_its_average():
    estimates = _estimate(_population({"A": (120, 120)}, change=100.0))

    cell = _cell(estimates, "A", "average_change")

    assert cell["standard_error"] == pytest.approx(0.0, abs=1e-9)
    assert (cell["value"], cell["lo"], cell["hi"]) == (100.0, 100.0, 100.0)
    assert cell["direction"] == "gain"


def test_intervals_are_reproducible_and_do_not_depend_on_the_chunk(monkeypatch):
    rng = np.random.default_rng(2)
    data = _population({"A": (150, 90), "B": (150, 70)})
    data["reformed"] = data["reformed"] + rng.normal(0.0, 80.0, 300) * (
        data["reformed"] != data["baseline"]
    )

    first = _estimate(data)._table
    again = _estimate(data)._table
    monkeypatch.setattr(estimate_module, "_REPLICATE_CHUNK", 37)
    chunked = _estimate(data)._table
    other_seed = _estimate(data, settings=DisclosureSettings(bootstrap_seed=1))._table

    pd.testing.assert_frame_equal(first, again)
    pd.testing.assert_frame_equal(first, chunked)
    assert not first["exact_lo"].equals(other_seed["exact_lo"])


def test_values_are_rounded_to_the_order_of_their_standard_error():
    rng = np.random.default_rng(4)
    data = _population({"A": (300, 200), "B": (300, 120)})
    data["reformed"] = data["baseline"] + rng.uniform(50.0, 2_000.0, 600) * (
        data["reformed"] != data["baseline"]
    )
    settings = DisclosureSettings()

    table = _estimate(data)._table

    for row in table[table["tier"] != WITHHELD].to_dict("records"):
        base = row["rounding_base"]
        assert base >= settings.min_rounding_base[row["outcome"]]
        assert math.log10(base) == pytest.approx(round(math.log10(base)))
        for column in ("value", "lo", "hi"):
            assert row[column] / base == pytest.approx(round(row[column] / base))
        assert row["lo"] <= row["value"] <= row["hi"]
        # The interval is rounded outward, never to the nearest step.
        assert row["lo"] <= row["exact_lo"] + 1e-9
        assert row["hi"] >= row["exact_hi"] - 1e-9
        if row["outcome"] != "share_no_change" and row["standard_error"] > base:
            assert base == 10.0 ** math.floor(math.log10(row["standard_error"]))
    average = _cell(_estimate(data), "A", "average_change")
    assert average["exact_lo"] < average["exact_value"] < average["exact_hi"]
    assert average["direction"] == "gain"


def test_rounding_goes_down_up_or_to_the_nearest_step():
    assert estimate_module._round(27.0, 10.0) == 30.0
    assert estimate_module._round(27.0, 10.0, "down") == 20.0
    assert estimate_module._round(23.0, 10.0, "up") == 30.0
    assert estimate_module._round(-23.0, 10.0, "down") == -30.0
    assert estimate_module._round(0.3, 0.1, "down") == 0.3
    assert estimate_module._round(0.0437, 0.001, "up") == 0.044


def test_an_interval_is_widened_to_include_its_estimate():
    """Skewed replicates can leave the estimate outside their percentiles."""
    draws = np.array([[2.0, 3.0, 4.0, 5.0], [2.0, 3.0, 4.0, 5.0]])

    lo, hi, error = estimate_module._interval(draws, np.array([10.0, 0.0]), 0.05)

    assert hi[0] == 10.0
    assert lo[1] == 0.0
    assert lo[0] == pytest.approx(2.15) and hi[1] == pytest.approx(4.85)
    assert error.tolist() == pytest.approx([np.std([2, 3, 4, 5], ddof=1)] * 2)


def test_an_interval_across_zero_is_too_close_to_call():
    rng = np.random.default_rng(6)
    data = _population({"A": (200, 0)})
    data["reformed"] = data["baseline"] + rng.choice([-500.0, 500.0], 200)

    cell = _cell(_estimate(data), "A", "average_change")

    assert cell["lo"] < 0 < cell["hi"]
    assert cell["direction"] == "too_close_to_call"


def test_relative_change_is_withheld_where_it_is_undefined():
    data = _population({"A": (60, 40)})
    data["reformed"] = data["reformed"] - data["baseline"]
    data["baseline"] = np.zeros(60)

    estimates = _estimate(data)

    relative = _cell(estimates, "A", "relative_change")
    assert (relative["tier"], relative["private_reason"]) == (
        WITHHELD,
        PRIVATE_UNDEFINED,
    )
    assert pd.isna(relative["value"])
    assert _cell(estimates, "A", "average_change")["tier"] != WITHHELD


def test_estimates_cannot_be_pickled_or_copied():
    """They hold exact values and, with noise on, the noise factors."""
    estimates = _estimate(_population({"A": (50, 30)}))

    with pytest.raises(TypeError, match="cannot be pickled"):
        pickle.dumps(estimates)
    with pytest.raises(TypeError, match="cannot be pickled"):
        copy.deepcopy(estimates)
    for name in ("table", "contributions", "source_index"):
        assert not hasattr(estimates, name)


def test_repr_holds_no_values():
    estimates = _estimate(_population({"A": (50, 30)}))

    assert repr(estimates) == (
        "AreaEstimates(level='constituency', reform='reform', year=2026, "
        "areas=1, private)"
    )


@pytest.mark.parametrize("field", ["baseline", "reformed", "source_ids"])
def test_inputs_must_have_one_entry_per_record(field):
    data = _population({"A": (50, 30)})
    data[field] = data[field][:10]

    with pytest.raises(ValueError, match="one entry per record"):
        _estimate(data)


def test_non_finite_inputs_raise():
    data = _population({"A": (50, 30)})
    data["reformed"][3] = np.nan

    with pytest.raises(ValueError, match="finite"):
        _estimate(data)
