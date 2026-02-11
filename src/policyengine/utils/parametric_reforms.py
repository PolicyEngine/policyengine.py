from collections.abc import Callable

from policyengine_core.periods import period

from policyengine.core import ParameterValue


def reform_dict_from_parameter_values(
    parameter_values: list[ParameterValue],
) -> dict:
    """
    Convert a list of ParameterValue objects to a reform dict format.

    This format is accepted by policyengine_us.Microsimulation(reform=...) and
    policyengine_uk.Microsimulation(reform=...) at construction time.

    Args:
        parameter_values: List of ParameterValue objects to convert.

    Returns:
        A dict mapping parameter names to period-value dicts, e.g.:
        {
            "gov.irs.deductions.standard.amount.SINGLE": {
                "2024-01-01": 29200
            }
        }
    """
    if not parameter_values:
        return None

    reform_dict = {}
    for pv in parameter_values:
        param_name = pv.parameter.name
        if param_name not in reform_dict:
            reform_dict[param_name] = {}

        # Format the period string
        period_str = pv.start_date.strftime("%Y-%m-%d")
        if pv.end_date:
            # Use period range format: "start.end"
            period_str = f"{period_str}.{pv.end_date.strftime('%Y-%m-%d')}"

        reform_dict[param_name][period_str] = pv.value

    return reform_dict


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
        return simulation

    return modifier
