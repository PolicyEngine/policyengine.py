"""Keyed noise factors. All ids and keys here are synthetic."""

import numpy as np
import pytest

from policyengine.disclosure import (
    NOISE_KEY_ENV,
    DisclosureKeyError,
    noise_factors,
    resolve_noise_key,
)
from policyengine.disclosure.noise import canonical_source_ids

TEST_KEY = b"test-key-for-unit-tests-only"


def test_factors_match_known_answers_for_the_test_key():
    """A change here re-draws the noise of every published table."""
    factors = noise_factors([123, "0123", 7, "2024:55"], TEST_KEY)

    assert factors.tolist() == pytest.approx(
        [
            0.88808850233229,
            1.1191625336822915,
            1.1148886386302803,
            1.0900808835347382,
        ],
        abs=1e-15,
    )


def test_factors_persist_across_calls_and_row_orders():
    ids = np.arange(500)
    shuffled = np.random.default_rng(0).permutation(ids)

    first = noise_factors(ids, TEST_KEY)
    second = noise_factors(shuffled, TEST_KEY)

    assert np.array_equal(first, noise_factors(ids, TEST_KEY))
    assert np.array_equal(first[shuffled], second)


def test_factors_stay_in_the_two_bands_with_nothing_near_one():
    factors = noise_factors(np.arange(20_000), TEST_KEY)

    low = (factors >= 0.88) & (factors <= 0.92)
    high = (factors >= 1.08) & (factors <= 1.12)
    assert (low | high).all()
    assert 0.45 < low.mean() < 0.55


def test_noise_distance_sets_the_bands():
    factors = noise_factors(np.arange(2_000), TEST_KEY, distance=(0.2, 0.3))

    assert (np.abs(factors - 1.0) >= 0.2).all()
    assert (np.abs(factors - 1.0) <= 0.3).all()


def test_id_types_name_the_same_household():
    factors = noise_factors([123, "123", 123.0, b"123", " 123 ", "0123"], TEST_KEY)

    assert len(set(factors[:5])) == 1
    assert factors[5] != factors[0]


def test_integer_and_string_arrays_agree():
    integers = noise_factors(np.array([5, 6, 7], dtype=np.int64), TEST_KEY)
    strings = noise_factors(np.array(["5", "6", "7"]), TEST_KEY)

    assert np.array_equal(integers, strings)


@pytest.mark.parametrize("bad", [[1, None], [1.0, float("nan")], ["a", " "], [1.5]])
def test_missing_blank_or_fractional_ids_raise(bad):
    with pytest.raises(ValueError):
        canonical_source_ids(bad)


def test_different_keys_give_different_factors():
    ids = np.arange(200)

    assert not np.array_equal(
        noise_factors(ids, TEST_KEY), noise_factors(ids, b"another-key-0123456789")
    )


@pytest.mark.parametrize("key", [None, "", "   ", b"", "short-key"])
def test_key_resolution_fails_closed(key, monkeypatch):
    monkeypatch.delenv(NOISE_KEY_ENV, raising=False)

    with pytest.raises(DisclosureKeyError):
        resolve_noise_key(key)


def test_key_comes_from_the_environment_and_the_argument_wins(monkeypatch):
    monkeypatch.setenv(NOISE_KEY_ENV, "environment-key-0123456789\n")

    assert resolve_noise_key() == b"environment-key-0123456789"
    assert resolve_noise_key("argument-key-0123456789") == b"argument-key-0123456789"


def test_key_error_never_shows_the_key(monkeypatch):
    monkeypatch.delenv(NOISE_KEY_ENV, raising=False)

    with pytest.raises(DisclosureKeyError) as error:
        resolve_noise_key("tooshort-secret")

    assert "tooshort-secret" not in str(error.value)
