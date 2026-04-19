"""Dispatch a flat ``extra_variables`` list to a per-entity mapping.

Callers pass a flat list — ``extra_variables=["adjusted_gross_income",
"state_agi", "is_medicaid_eligible"]`` — and the library looks up each
name on the country model to figure out which entity it belongs on.
Unknown names raise with a close-match suggestion.
"""

from __future__ import annotations

from collections.abc import Iterable
from difflib import get_close_matches
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion


def dispatch_extra_variables(
    *,
    model_version: TaxBenefitModelVersion,
    names: Iterable[str],
) -> dict[str, list[str]]:
    """Group ``names`` by the entity each variable lives on.

    Raises :class:`ValueError` if any name is not defined on the model.
    """
    by_entity: dict[str, list[str]] = {}
    unknown: list[str] = []

    variables_by_name = model_version.variables_by_name
    for name in names:
        variable = variables_by_name.get(name)
        if variable is None:
            unknown.append(name)
            continue
        by_entity.setdefault(variable.entity, []).append(name)

    if unknown:
        lines = [
            f"extra_variables contains names not defined on "
            f"{model_version.model.id} {model_version.version}:",
        ]
        for name in unknown:
            suggestions = get_close_matches(
                name, list(variables_by_name), n=1, cutoff=0.7
            )
            suggestion = f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
            lines.append(f"  - '{name}'{suggestion}")
        raise ValueError("\n".join(lines))

    return by_entity
