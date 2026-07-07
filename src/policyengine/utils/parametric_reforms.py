from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Optional, Union

from policyengine_core.periods import period

from policyengine.core import ParameterValue

if TYPE_CHECKING:
    from policyengine.core.dynamic import Dynamic
    from policyengine.core.policy import Policy

# policyengine-core's Reform.from_dict applies a bare "YYYY-MM-DD" period
# key for a single instant only, so open-ended values (end_date=None) need
# an explicit far-future stop to hold beyond their start year (#453).
OPEN_ENDED_REFORM_STOP = "2100-12-31"


def _open_ended_stop_str(pv: ParameterValue, siblings: list[ParameterValue]) -> str:
    """Stop date for an open-ended value: the day before the next-later
    value of the same parameter starts, or far-future if none follows."""
    later_starts = [
        other.start_date for other in siblings if other.start_date > pv.start_date
    ]
    if later_starts:
        return (min(later_starts) - timedelta(days=1)).strftime("%Y-%m-%d")
    return OPEN_ENDED_REFORM_STOP


def reform_dict_from_parameter_values(
    parameter_values: Optional[list[ParameterValue]],
) -> Optional[dict]:
    """
    Convert a list of ParameterValue objects to a reform dict format.

    This format is accepted by policyengine_us.Microsimulation(reform=...) and
    policyengine_uk.Microsimulation(reform=...) at construction time.

    Every period key uses the "start.stop" range format. Values with
    end_date=None run from their start date until the next-later value of
    the same parameter takes over, or until OPEN_ENDED_REFORM_STOP.

    Args:
        parameter_values: List of ParameterValue objects to convert.

    Returns:
        A dict mapping parameter names to period-value dicts, e.g.:
        {
            "gov.irs.deductions.standard.amount.SINGLE": {
                "2024-01-01.2100-12-31": 29200
            }
        }
    """
    if not parameter_values:
        return None

    by_parameter: dict[str, list[ParameterValue]] = {}
    for pv in parameter_values:
        by_parameter.setdefault(pv.parameter.name, []).append(pv)

    reform_dict: dict[str, dict] = {}
    for param_name, values in by_parameter.items():
        periods = reform_dict.setdefault(param_name, {})
        for pv in values:
            start_str = pv.start_date.strftime("%Y-%m-%d")
            if pv.end_date:
                stop_str = pv.end_date.strftime("%Y-%m-%d")
            else:
                stop_str = _open_ended_stop_str(pv, values)
            periods[f"{start_str}.{stop_str}"] = pv.value

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
            p = simulation.tax_benefit_system.parameters.get_child(pv.parameter.name)
            start_period = period(pv.start_date.strftime("%Y-%m-%d"))
            stop_period = (
                period(pv.end_date.strftime("%Y-%m-%d")) if pv.end_date else None
            )
            p.update(
                value=pv.value,
                start=start_period,
                stop=stop_period,
            )
        return simulation

    return modifier


def build_reform_dict(
    policy_or_dynamic: Optional[Union[Policy, Dynamic]],
) -> Optional[dict]:
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
        return reform_dict_from_parameter_values(policy_or_dynamic.parameter_values)
    return None


def merge_reform_dicts(
    base: Optional[dict], override: Optional[dict]
) -> Optional[dict]:
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
