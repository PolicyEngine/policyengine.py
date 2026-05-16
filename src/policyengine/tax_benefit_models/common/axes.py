"""Axes helpers for household calculators."""

from __future__ import annotations

from collections.abc import Mapping
from difflib import get_close_matches
from typing import Any, Optional

from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion


def normalize_axes(
    *,
    axes: Optional[list[Any]],
    year: int,
    model_version: TaxBenefitModelVersion,
) -> Optional[list[list[dict[str, Any]]]]:
    """Validate and periodise household-calculator axes.

    The country packages expect the lower-level OpenFisca/PolicyEngine Core
    shape: ``[[{"name": ..., "min": ..., "max": ..., "count": ...}]]``.
    For convenience, callers may also pass a flat list of axis dictionaries.
    Missing ``period`` values default to the household calculator's ``year``.
    """
    if axes is None:
        return None
    if not isinstance(axes, list) or not axes:
        raise ValueError("axes must be a non-empty list of axis dictionaries.")

    axis_groups = axes if isinstance(axes[0], list) else [axes]
    normalized: list[list[dict[str, Any]]] = []
    variables_by_name = model_version.variables_by_name

    for group in axis_groups:
        if not isinstance(group, list) or not group:
            raise ValueError("each axes group must be a non-empty list.")

        normalized_group: list[dict[str, Any]] = []
        for axis in group:
            if not isinstance(axis, Mapping):
                raise ValueError("each axis must be a dictionary.")

            axis_dict = dict(axis)
            name = axis_dict.get("name")
            if not isinstance(name, str):
                raise ValueError("each axis must include a string 'name'.")
            if name not in variables_by_name:
                suggestions = get_close_matches(
                    name, list(variables_by_name), n=1, cutoff=0.7
                )
                suggestion = (
                    f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
                )
                raise ValueError(
                    f"axis variable '{name}' is not defined on "
                    f"{model_version.model.id} {model_version.version}{suggestion}"
                )

            for required_key in ("min", "max", "count"):
                if required_key not in axis_dict:
                    raise ValueError(f"axis '{name}' must include '{required_key}'.")

            axis_dict.setdefault("period", year)
            normalized_group.append(axis_dict)

        normalized.append(normalized_group)

    return normalized


def values_for_entity(
    values: list[Any],
    *,
    entity_index: int,
    entity_count: int,
    axes_active: bool,
):
    """Return scalar or axis-series values for one entity member."""
    if not axes_active:
        return values[entity_index]
    return values[entity_index::entity_count]
