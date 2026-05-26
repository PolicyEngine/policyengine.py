"""Helpers for conditionally materialized output variables."""

from __future__ import annotations

from policyengine.core import Simulation


def add_extra_variables(
    simulation: Simulation,
    variables_by_entity: dict[str, list[str]],
) -> None:
    """Append extra output variables without dropping caller-supplied extras."""
    extra_variables = {
        entity: list(variables)
        for entity, variables in (simulation.extra_variables or {}).items()
    }
    for entity, variables in variables_by_entity.items():
        existing = extra_variables.setdefault(entity, [])
        for variable in variables:
            if variable not in existing:
                existing.append(variable)
    simulation.extra_variables = extra_variables
