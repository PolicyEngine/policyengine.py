from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from policyengine_core.periods import period

from policyengine.core import ParameterValue

if TYPE_CHECKING:
    from policyengine.core.dynamic import Dynamic
    from policyengine.core.policy import Policy


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


def build_reform_dict(policy_or_dynamic: Policy | Dynamic | None) -> dict | None:
    """Extract a reform dict from a Policy or Dynamic object.

    If the object has parameter_values, converts them to reform dict format.
    Returns None if the object is None or has no parameter values.

    Args:
        policy_or_dynamic: A Policy or Dynamic object, or None.

    Returns:
        A reform dict suitable for Microsimulation(reform=...), or None.
    """
    if policy_or_dynamic is None:
        return None
    if policy_or_dynamic.parameter_values:
        return reform_dict_from_parameter_values(
            policy_or_dynamic.parameter_values
        )
    return None


def merge_reform_dicts(
    base: dict | None, override: dict | None
) -> dict | None:
    """Merge two reform dicts, with override values taking precedence.

    Either or both dicts can be None. When both have entries for the same
    parameter, period-level values from override replace those in base.

    Args:
        base: The base reform dict (e.g., from policy).
        override: The override reform dict (e.g., from dynamic).

    Returns:
        The merged reform dict, or None if both inputs are None.
    """
    if base is None:
        return override
    if override is None:
        return base

    merged = {k: dict(v) for k, v in base.items()}
    for param_name, period_values in override.items():
        if param_name not in merged:
            merged[param_name] = {}
        merged[param_name].update(period_values)
    return merged
