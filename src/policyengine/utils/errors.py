"""Shared helpers for constructing consistent errors."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Optional


def format_conditional_error_detail(
    label: str,
    values: Iterable[str],
) -> Optional[str]:
    """Build a labelled error detail line when ``values`` is non-empty."""
    sorted_values = sorted(set(values))
    if not sorted_values:
        return None
    return f"{label}: {', '.join(sorted_values)}"
