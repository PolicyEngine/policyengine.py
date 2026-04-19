"""Strict validation for household-calculation inputs.

Catches the three typo classes that otherwise silently propagate wrong
numbers to published results:

1. Unknown variable name entirely (``employment_incme``).
2. Valid variable placed on the wrong entity (``filing_status`` passed
   to ``people`` instead of ``tax_unit``).
3. Empty ``people`` list (policyengine_us will IndexError deep in
   simulation).

All errors include paste-able fixes.
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
    """Raise ``ValueError`` on unknown or mis-placed entity variables.

    ``entities`` maps entity name → iterable of entity dicts. Each key
    is checked against ``model_version.variables_by_name``:

    - If the key is unknown, the error includes a difflib close-match
      suggestion.
    - If the key is a known variable but defined on a different entity,
      the error names the correct entity and shows the kwarg swap.
    """
    if "person" in entities and not list(entities["person"]):
        raise ValueError(
            "people must be a non-empty list. At minimum pass people=[{'age': <int>}]."
        )

    variables_by_name = model_version.variables_by_name
    valid_names = set(variables_by_name)
    unknown: list[tuple[str, str]] = []
    misplaced: list[tuple[str, str, str]] = []

    for entity_name, records in entities.items():
        for record in records:
            for key in record:
                if key in _STRUCTURAL_KEYS:
                    continue
                variable = variables_by_name.get(key)
                if variable is None:
                    unknown.append((entity_name, key))
                elif variable.entity != entity_name:
                    misplaced.append((entity_name, key, variable.entity))

    if not unknown and not misplaced:
        return

    lines: list[str] = []
    if unknown:
        lines.append(
            f"Unknown variable names on {model_version.model.id} "
            f"{model_version.version}:"
        )
        for entity_name, key in unknown:
            suggestions = get_close_matches(key, valid_names, n=1, cutoff=0.7)
            hint = f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
            lines.append(f"  - {entity_name}: '{key}'{hint}")
        if not misplaced:
            first_bad = unknown[0][1]
            lines.append(
                f"If '{first_bad}' is a real variable outside the default "
                f"output columns, pass it via extra_variables=['{first_bad}']."
            )
    if misplaced:
        if lines:
            lines.append("")
        lines.append("Variables passed on the wrong entity:")
        for wrong_entity, key, correct_entity in misplaced:
            lines.append(
                f"  - '{key}' was given on {wrong_entity}; it belongs on "
                f"{correct_entity}. Move it: pass "
                f"{correct_entity}={{'{key}': <value>}}."
            )

    raise ValueError("\n".join(lines))
