"""RFC 8785 canonical JSON used for receipt digests.

``policyengine.provenance.canonical`` is checked against the independent
``rfc8785`` implementation (a differential test), against the RFC's own
examples, and for the properties every canonical form needs.
"""

import json
import math
from pathlib import Path

import pytest
import rfc8785
from hypothesis import given, settings
from hypothesis import strategies as st

from policyengine.provenance.canonical import (
    MAX_SAFE_INTEGER,
    CanonicalJSONError,
    canonical_json,
    canonical_sha256,
    drop_null_members,
)

# Strings without unpaired surrogates: those have no UTF-8 form.
TEXT = st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=12)
FINITE = st.floats(allow_nan=False, allow_infinity=False)
SAFE_INT = st.integers(min_value=-MAX_SAFE_INTEGER, max_value=MAX_SAFE_INTEGER)
JSON_VALUES = st.recursive(
    st.none() | st.booleans() | SAFE_INT | FINITE | TEXT,
    lambda children: (
        st.lists(children, max_size=4) | st.dictionaries(TEXT, children, max_size=4)
    ),
    max_leaves=20,
)


@settings(max_examples=500, deadline=None)
@given(JSON_VALUES)
def test_matches_the_rfc8785_reference_implementation(value):
    assert canonical_json(value) == rfc8785.dumps(value)


@settings(max_examples=2000, deadline=None)
@given(FINITE)
def test_numbers_match_the_reference_implementation(number):
    assert canonical_json(number) == rfc8785.dumps(number)


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        # RFC 8785 section 3.2.2.3 and appendix B examples.
        (333333333.33333329, b"333333333.3333333"),
        (1e30, b"1e+30"),
        (4.50, b"4.5"),
        (2e-3, b"0.002"),
        (0.000000000000000000000000001, b"1e-27"),
        (-0.0, b"0"),
        (1e21, b"1e+21"),
        (1e20, b"100000000000000000000"),
        (1e-7, b"1e-7"),
        (1.5e16, b"15000000000000000"),
        (5e-324, b"5e-324"),
        (1.7976931348623157e308, b"1.7976931348623157e+308"),
    ],
)
def test_rfc8785_number_examples(number, expected):
    assert canonical_json(number) == expected


def test_rfc8785_member_ordering_example():
    value = {
        "€": "Euro Sign",
        "\r": "Carriage Return",
        "דּ": "Hebrew Letter Dalet With Dagesh",
        "1": "One",
        "\U0001f600": "Emoji: Grinning Face",
        "\u0080": "Control",
        "ö": "Latin Small Letter O With Diaeresis",
    }
    keys = list(json.loads(canonical_json(value)))
    assert keys == ["\r", "1", "\u0080", "ö", "€", "\U0001f600", "דּ"]


@settings(max_examples=300, deadline=None)
@given(JSON_VALUES)
def test_canonical_form_is_a_fixed_point(value):
    once = canonical_json(value)
    assert canonical_json(_read_as_jcs_consumer(once)) == once


@settings(max_examples=300, deadline=None)
@given(st.dictionaries(TEXT, JSON_VALUES, max_size=6), st.randoms())
def test_member_order_does_not_change_bytes(mapping, random):
    items = list(mapping.items())
    random.shuffle(items)
    assert canonical_json(dict(items)) == canonical_json(mapping)


@settings(max_examples=300, deadline=None)
@given(FINITE)
def test_numbers_round_trip_exactly(number):
    # RFC 8785 numbers are doubles; read them back as doubles.
    parsed = json.loads(canonical_json(number), parse_int=float)
    assert parsed == number


@pytest.mark.parametrize(
    "value",
    [
        math.nan,
        math.inf,
        -math.inf,
        2**53,
        -(2**53),
        10**400,
        "\ud800",
        {1: "non-string key"},
        b"bytes",
        object(),
    ],
)
def test_refuses_values_without_one_canonical_form(value):
    with pytest.raises(CanonicalJSONError):
        canonical_json(value)


def test_large_integer_valued_doubles_are_written_as_doubles():
    assert canonical_json(float(2**53)) == b"9007199254740992"
    assert canonical_json(1e22) == b"1e+22"


def _read_as_jcs_consumer(text: bytes):
    """Parse as a double-based consumer would: unsafe integers are doubles."""

    def parse_int(literal: str):
        number = int(literal)
        return number if abs(number) <= MAX_SAFE_INTEGER else float(literal)

    return json.loads(text, parse_int=parse_int)


def test_digest_is_sha256_of_canonical_bytes():
    import hashlib

    value = {"b": [1, 2.5, None], "a": "é"}
    assert canonical_sha256(value) == hashlib.sha256(canonical_json(value)).hexdigest()


@settings(max_examples=300, deadline=None)
@given(JSON_VALUES)
def test_dropping_null_members_leaves_no_null_member(value):
    def has_null_member(item):
        if isinstance(item, dict):
            return any(v is None or has_null_member(v) for v in item.values())
        if isinstance(item, list):
            return any(has_null_member(v) for v in item)
        return False

    stripped = drop_null_members(value)
    assert not has_null_member(stripped)
    assert drop_null_members(stripped) == stripped


FIXTURES = Path(__file__).parent / "fixtures" / "uk_replay"


@pytest.mark.parametrize(
    ("name", "digest_key", "drop"),
    [
        ("qualification_request_golden", "request_id", None),
        ("replay_receipt_golden", "receipt_sha256", "receipt_sha256"),
    ],
)
def test_reproduces_the_scorecard_golden_bytes(name, digest_key, drop):
    """Cross-implementation check against the replay corpus owner's fixtures."""

    import hashlib

    value = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    if drop:
        value.pop(drop)
    expected = (FIXTURES / f"{name}.jcs").read_bytes()
    assert canonical_json(value) == expected
    digests = json.loads((FIXTURES / "DIGESTS.json").read_text())
    assert canonical_sha256(value) == digests[f"{name}.json"][digest_key]
    assert hashlib.sha256(expected).hexdigest() == digests[f"{name}.json"][digest_key]
