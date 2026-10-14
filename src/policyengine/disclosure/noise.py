"""Keyed noise: one fixed factor for each source household.

Every source household gets a multiplicative factor a set distance from 1,
derived from its id and a secret key with HMAC-SHA256. The same household
has the same factor in every table and in every rebuild, so repeated
publication cannot average the noise away.
"""

import hashlib
import hmac
import os
from numbers import Integral, Real
from typing import Optional, Union

import numpy as np
import pandas as pd

NOISE_KEY_ENV = "POLICYENGINE_DISCLOSURE_NOISE_KEY"
MIN_KEY_BYTES = 16
_FACTOR_LABEL = b"policyengine.disclosure.noise-factor.v1\x00"


class DisclosureKeyError(ValueError):
    """The noise key is missing or unusable. The message never holds the key."""


def resolve_noise_key(key: Optional[Union[str, bytes]] = None) -> bytes:
    """Return the noise key from the argument, else from the environment.

    There is no default key: a key in code is a public key.
    """
    candidate = key if key is not None else os.environ.get(NOISE_KEY_ENV)
    if candidate is None:
        raise DisclosureKeyError(
            f"Noise is on but no key is set: pass noise_key= or set {NOISE_KEY_ENV}."
        )
    raw = candidate.encode("utf-8") if isinstance(candidate, str) else bytes(candidate)
    raw = raw.strip()
    if not raw:
        raise DisclosureKeyError(f"The noise key is empty: check {NOISE_KEY_ENV}.")
    if len(raw) < MIN_KEY_BYTES:
        raise DisclosureKeyError(
            f"The noise key is shorter than {MIN_KEY_BYTES} bytes."
        )
    return raw


def _canonical_id(value: object) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("A source household id is blank.")
        return text
    if isinstance(value, bool | np.bool_):
        raise ValueError("A source household id is a boolean.")
    if isinstance(value, Integral):
        return str(int(value))
    if isinstance(value, Real):
        number = float(value)
        if not np.isfinite(number) or not number.is_integer():
            raise ValueError("A source household id is not a whole number.")
        return str(int(number))
    raise ValueError(f"Unsupported source household id type: {type(value).__name__}.")


def canonical_source_ids(source_ids: object) -> np.ndarray:
    """Return one canonical string per row.

    123, 123.0, "123" and b"123" name the same household. "0123" does not.
    A missing or blank id raises: a row with no source cannot be counted.
    """
    series = pd.Series(source_ids)
    if series.isna().any():
        raise ValueError("A source household id is missing.")
    codes, uniques = pd.factorize(series.astype(object), use_na_sentinel=True)
    canonical = np.array([_canonical_id(value) for value in uniques], dtype=object)
    return np.asarray(canonical[codes])


def _factor(canonical_id: str, key: bytes, distance: tuple[float, float]) -> float:
    digest = hmac.new(
        key, _FACTOR_LABEL + canonical_id.encode("utf-8"), hashlib.sha256
    ).digest()
    fraction = int.from_bytes(digest[:8], "big") / 2**64
    low, high = distance
    magnitude = low + (high - low) * fraction
    return 1.0 + magnitude if digest[8] & 1 else 1.0 - magnitude


def noise_factors(
    source_ids: object,
    key: bytes,
    *,
    distance: tuple[float, float] = (0.08, 0.12),
) -> np.ndarray:
    """Return the noise factor of each row's source household."""
    canonical = canonical_source_ids(source_ids)
    codes, uniques = pd.factorize(canonical)
    factors = np.array([_factor(value, key, distance) for value in uniques])
    return np.asarray(factors[codes])
