"""Strict validation for household-calculation inputs.

Surfaces typos (``employment_incme``) that would otherwise silently
default to zero. Error messages include paste-able fixes — a close
variable-name match via :mod:`difflib` plus a hint to use
``extra_variables`` when the name is valid but outside the default set.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from difflib import get_close_matches
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion


_STRUCTURAL_KEYS = frozenset(
    {
        "id",
        "members",
        "person_id",
        "household_id",
        "marital_unit_id",
        "family_id",
        "spm_unit_id",
        "tax_unit_id",
        "benunit_id",
        "person_weight",
        "household_weight",
        "marital_unit_weight",
        "family_weight",
        "spm_unit_weight",
        "tax_unit_weight",
        "benunit_weight",
    }
)


def validate_household_input(
    *,
    model_version: TaxBenefitModelVersion,
    entities: Mapping[str, Iterable[Mapping[str, object]]],
) -> None:
    """Raise ``ValueError`` if any entity dict contains an unknown variable.

    ``entities`` maps entity name → iterable of entity dicts. Each dict
    is checked against ``model_version.variables_by_name``; unknown
    keys are reported with a close-match suggestion.
    """
    valid = set(model_version.variables_by_name)
    problems: list[tuple[str, str]] = []
    for entity_name, records in entities.items():
        for record in records:
            for key in record:
                if key in _STRUCTURAL_KEYS:
                    continue
                if key not in valid:
                    problems.append((entity_name, key))

    if not problems:
        return

    lines = [
        "Household input contains variable names not defined on "
        f"{model_version.model.id} {model_version.version}:",
    ]
    for entity_name, key in problems:
        suggestions = get_close_matches(key, valid, n=1, cutoff=0.7)
        suggestion = f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
        lines.append(f"  - {entity_name}: '{key}'{suggestion}")
    first_bad = problems[0][1]
    lines.append(
        f"If '{first_bad}' is a real variable outside the default output "
        f"columns, pass it via extra_variables=['{first_bad}'] instead."
    )
    raise ValueError("\n".join(lines))
