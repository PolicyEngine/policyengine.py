"""Cross-language canonical JSON and content digests for receipts.

Receipts are hashed in Python (this package, the scorecard), JavaScript (the
Budget dashboard) and other consumers, so their digests use the JSON
Canonicalization Scheme (RFC 8785) rather than Python's ``json.dumps``
spelling. Two implementations that agree on RFC 8785 produce identical bytes
for the same JSON value, so a digest computed anywhere can be checked
anywhere.

RFC 8785 in brief:

- object members are sorted by the UTF-16 code units of their names;
- no insignificant whitespace;
- strings are escaped as ECMAScript ``JSON.stringify`` escapes them, and
  everything else is written as literal UTF-8;
- numbers are written as ECMAScript ``Number.prototype.toString`` writes
  IEEE 754 doubles.

The TRACE TRO digests in :mod:`policyengine.provenance.trace` keep their own
documented serialization; this module is for receipt contracts.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any

__all__ = [
    "CanonicalJSONError",
    "canonical_json",
    "canonical_sha256",
    "drop_null_members",
    "MAX_SAFE_INTEGER",
]

#: Largest integer every IEEE 754 double consumer reads exactly (2**53 - 1).
#: Larger integers are refused, as the rfc8785 reference implementation does.
MAX_SAFE_INTEGER = 2**53 - 1

_SHORT_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


class CanonicalJSONError(ValueError):
    """Raised for values RFC 8785 cannot serialize identically everywhere."""


def _string(value: str) -> str:
    parts = ['"']
    for character in value:
        escaped = _SHORT_ESCAPES.get(character)
        if escaped is not None:
            parts.append(escaped)
            continue
        code_point = ord(character)
        if code_point < 0x20:
            parts.append(f"\\u{code_point:04x}")
        elif 0xD800 <= code_point <= 0xDFFF:
            raise CanonicalJSONError(
                "Strings with unpaired surrogate code points have no canonical "
                "UTF-8 form."
            )
        else:
            parts.append(character)
    parts.append('"')
    return "".join(parts)


def _number(value: float) -> str:
    """Write a double as ECMAScript ``Number.prototype.toString`` does."""
    if math.isnan(value) or math.isinf(value):
        raise CanonicalJSONError("NaN and infinite numbers are not valid JSON.")
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    # ``repr`` gives the shortest digit string that round-trips, which is the
    # digit string ECMAScript uses; only the layout around it differs.
    # ``float(...)`` first: subclasses such as ``numpy.float64`` have their own
    # ``repr`` (``np.float64(1.5)``), which is not a JSON number.
    mantissa, _, exponent_text = repr(float(abs(value))).partition("e")
    integer_part, _, fraction_part = mantissa.partition(".")
    all_digits = integer_part + fraction_part
    # ``point`` counts digits before the decimal point in ``all_digits``.
    point = len(integer_part) + (int(exponent_text) if exponent_text else 0)
    significant = all_digits.lstrip("0")
    point -= len(all_digits) - len(significant)
    digits = significant.rstrip("0")
    # ECMAScript names: value = digits * 10 ** (n - k).
    k = len(digits)
    n = point
    if k <= n <= 21:
        text = digits + "0" * (n - k)
    elif 0 < n <= 21:
        text = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        text = "0." + "0" * (-n) + digits
    else:
        exponent_sign = "+" if n - 1 >= 0 else "-"
        tail = digits[0] if k == 1 else digits[0] + "." + digits[1:]
        text = f"{tail}e{exponent_sign}{abs(n - 1)}"
    return sign + text


def _serialize(value: Any, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, str):
        out.append(_string(value))
    elif isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            # Matches the rfc8785 reference implementation, which refuses
            # integers it cannot be sure every consumer reads identically.
            raise CanonicalJSONError(
                f"Integer {value} is outside +/-(2**53 - 1); write it as a "
                "string or a float."
            )
        # ``int.__repr__`` ignores an int subclass's own ``__str__``/``__repr__``
        # (``IntEnum`` members are written as their value).
        out.append(int.__repr__(int(value)))
    elif isinstance(value, float):
        out.append(_number(value))
    elif isinstance(value, Mapping):
        items = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalJSONError(
                    f"Object member names must be strings, got {type(key).__name__}."
                )
            items.append((key, item))
        items.sort(key=lambda pair: pair[0].encode("utf-16-be", "surrogatepass"))
        out.append("{")
        for index, (key, item) in enumerate(items):
            if index:
                out.append(",")
            out.append(_string(key))
            out.append(":")
            _serialize(item, out)
        out.append("}")
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        out.append("[")
        for index, item in enumerate(value):
            if index:
                out.append(",")
            _serialize(item, out)
        out.append("]")
    else:
        raise CanonicalJSONError(
            f"{type(value).__name__} is not a JSON value; serialize it first."
        )


def canonical_json(value: Any) -> bytes:
    """Return the RFC 8785 canonical UTF-8 bytes of a JSON value."""

    out: list[str] = []
    try:
        _serialize(value, out)
    except RecursionError as exc:
        raise CanonicalJSONError(
            "The value is nested too deeply to serialize."
        ) from exc
    return "".join(out).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return the lowercase hex SHA-256 of a value's canonical JSON bytes."""

    return hashlib.sha256(canonical_json(value)).hexdigest()


def drop_null_members(value: Any) -> Any:
    """Remove object members whose value is ``null``, recursively.

    Receipt digests are taken after this step, so a producer that writes
    ``"field": null`` and one that omits the field compute the same digest.
    Array elements are kept as they are.
    """

    if isinstance(value, Mapping):
        return {
            key: drop_null_members(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [drop_null_members(item) for item in value]
    return value
