from policyengine.core import ParameterValue
from typing import Callable


def simulation_modifier_from_parameter_values(parameter_values: list[ParameterValue]) -> Callable:
    """
    Create a simulation modifier function that applies the given parameter values to a simulation.

    Args:
        parameter_values (list[ParameterValue]): List of ParameterValue objects to apply.

    Returns:
        Callable: A function that takes a Simulation object and applies the parameter values.
    """

    def modifier(simulation):
        for pv in parameter_values:
            p = simulation.tax_benefit_system.parameters.get_child(pv.parameter.name)
            p.update(
                value=pv.value,
                start=pv.start_date.strftime("%Y-%m-%d"),
                stop=pv.stop_date.strftime("%Y-%m-%d") if pv.stop_date else None,
            )
        return simulation

    return modifier