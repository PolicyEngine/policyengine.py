from collections.abc import Callable

from policyengine_core.periods import period

from policyengine.core import ParameterValue


def simulation_modifier_from_parameter_values(
    parameter_values: list[ParameterValue],
) -> Callable:
    """
    Create a simulation modifier function that applies the given parameter values to a simulation.

    Args:
        parameter_values (list[ParameterValue]): List of ParameterValue objects to apply.

    Returns:
        Callable: A function that takes a Simulation object and applies the parameter values.
    """

    def modifier(simulation):
        for pv in parameter_values:
            p = simulation.tax_benefit_system.parameters.get_child(
                pv.parameter.name
            )
            start_period = period(pv.start_date.strftime("%Y-%m-%d"))
            stop_period = (
                period(pv.end_date.strftime("%Y-%m-%d"))
                if pv.end_date
                else None
            )
            p.update(
                value=pv.value,
                start=start_period,
                stop=stop_period,
            )

        # Clear caches so calculations use updated parameter values
        simulation.tax_benefit_system.reset_parameter_caches()

        # Clear computed variable caches (but preserve input variables)
        # Variables with formulas are computed; those without are inputs
        for population in simulation.populations.values():
            for var_name, holder in population._holders.items():
                variable = simulation.tax_benefit_system.get_variable(var_name)
                if variable.formulas:  # Only clear computed variables
                    holder.delete_arrays()

        return simulation

    return modifier
