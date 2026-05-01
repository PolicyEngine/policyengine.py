"""Program-statistics specifications for the US model.

The program list used by ``economic_impact_analysis`` was previously a
hard-coded ``dict`` literal that duplicated each program's ``entity``
inline. That design is fragile — when ``policyengine-us`` moves a
variable between entities, or renames it, the hard-coded entity falls
out of sync silently and only fails at simulation time deep inside an
``Aggregate`` lookup.

This module replaces that pattern with:

* A structured :class:`ProgramSpec` declaring just the variable name
  and whether the program is a tax (entity is *not* duplicated here).
* :func:`resolve_program_specs`, which validates every spec against the
  model up front and derives ``entity`` from each variable's own
  metadata. Unknown variables produce a single :class:`ValueError`
  listing all problems at once, with fuzzy-match suggestions.

This is a step toward the durable design tracked in #326; it does not
yet derive the program list itself from model metadata (e.g. by
scanning for variables tagged as ``program``), but it removes the
entity-drift class of bug entirely.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from policyengine.core import TaxBenefitModelVersion


@dataclass(frozen=True)
class ProgramSpec:
    """Declarative entry for a single program in the program-statistics table.

    Attributes:
        name: Variable name in the model (also used as the display label).
        is_tax: ``True`` for taxes (winner/loser sign is inverted), ``False``
            for benefits.
    """

    name: str
    is_tax: bool


@dataclass(frozen=True)
class ResolvedProgram:
    """A :class:`ProgramSpec` after metadata-driven validation."""

    name: str
    entity: str
    is_tax: bool


# US program list. Variable names must match what `policyengine-us`
# actually exposes; entity is derived from each variable's metadata
# at resolve-time and does not need to be repeated here.
US_PROGRAM_SPECS: list[ProgramSpec] = [
    ProgramSpec(name="income_tax", is_tax=True),
    ProgramSpec(name="employee_payroll_tax", is_tax=True),
    ProgramSpec(name="household_state_income_tax", is_tax=True),
    ProgramSpec(name="snap", is_tax=False),
    ProgramSpec(name="tanf", is_tax=False),
    ProgramSpec(name="ssi", is_tax=False),
    ProgramSpec(name="social_security", is_tax=False),
    ProgramSpec(name="medicare_cost", is_tax=False),
    ProgramSpec(name="medicaid", is_tax=False),
    ProgramSpec(name="eitc", is_tax=False),
    ProgramSpec(name="ctc", is_tax=False),
]


def resolve_program_specs(
    specs: list[ProgramSpec],
    model_version: TaxBenefitModelVersion,
) -> list[ResolvedProgram]:
    """Validate every spec against the model and derive its entity.

    Collects all unknown-variable errors into a single
    :class:`ValueError` so the caller sees the full list of problems
    at once instead of fixing them one at a time. Includes
    ``difflib`` suggestions for likely typos / renames.

    Raises:
        ValueError: if any spec references a variable not present in
            ``model_version``.
    """
    known = model_version.variables_by_name
    errors: list[str] = []
    resolved: list[ResolvedProgram] = []

    for spec in specs:
        variable = known.get(spec.name)
        if variable is None:
            suggestions = difflib.get_close_matches(spec.name, known.keys(), n=3)
            msg = f"{spec.name!r}: variable not found in model"
            if suggestions:
                msg += f" (did you mean: {', '.join(suggestions)}?)"
            errors.append(msg)
            continue
        resolved.append(
            ResolvedProgram(
                name=spec.name,
                entity=variable.entity,
                is_tax=spec.is_tax,
            )
        )

    if errors:
        joined = "\n  - ".join(errors)
        raise ValueError(
            f"Invalid program-statistics configuration ({len(errors)} "
            f"unknown variables):\n  - {joined}"
        )

    return resolved
