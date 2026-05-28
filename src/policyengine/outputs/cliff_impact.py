"""Legacy-compatible tax-benefit cliff macro output."""

from __future__ import annotations

from pydantic import BaseModel

from policyengine.core import Output, Simulation
from policyengine.outputs.aggregate import (
    get_aggregate_variable,
    get_output_entity_data,
    require_output_column,
)
from policyengine.outputs.extra_variables import add_extra_variables

CLIFF_IMPACT_VARIABLES = ("cliff_gap", "is_on_cliff", "is_adult")


class CliffImpactInSimulation(BaseModel):
    cliff_gap: float
    cliff_share: float


class CliffImpact(Output):
    baseline: CliffImpactInSimulation
    reform: CliffImpactInSimulation


def _cliff_variables_by_entity(
    simulation: Simulation,
) -> dict[str, list[str]]:
    variables_by_entity: dict[str, list[str]] = {}
    for variable_name in CLIFF_IMPACT_VARIABLES:
        variable = get_aggregate_variable(
            simulation,
            variable_name,
            "CliffImpact.extra_variables",
        )
        variables_by_entity.setdefault(variable.entity, []).append(variable_name)
    return variables_by_entity


def configure_cliff_impact_variables(*simulations: Simulation) -> None:
    """Materialize cliff columns only for analyses that request them."""
    for simulation in simulations:
        add_extra_variables(
            simulation,
            _cliff_variables_by_entity(simulation),
        )


def _sum_output_variable(
    simulation: Simulation,
    variable_name: str,
) -> float:
    context = f"CliffImpact.{variable_name}"
    variable = get_aggregate_variable(simulation, variable_name, context)
    data = get_output_entity_data(simulation, variable.entity, context)
    require_output_column(
        data,
        variable_name,
        variable.entity,
        simulation,
        context,
    )
    return float(data[variable_name].sum())


def _calculate_cliff_impact_in_simulation(
    simulation: Simulation,
) -> CliffImpactInSimulation:
    cliff_gap = _sum_output_variable(simulation, "cliff_gap")
    people_on_cliffs = _sum_output_variable(simulation, "is_on_cliff")
    adults = _sum_output_variable(simulation, "is_adult")

    return CliffImpactInSimulation(
        cliff_gap=cliff_gap,
        cliff_share=float(people_on_cliffs / adults),
    )


def calculate_cliff_impact(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> CliffImpact:
    """Calculate legacy macro cliff output from materialized simulations."""
    return CliffImpact(
        baseline=_calculate_cliff_impact_in_simulation(baseline_simulation),
        reform=_calculate_cliff_impact_in_simulation(reform_simulation),
    )
