"""Legacy-compatible labor-supply response macro output."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from microdf import MicroSeries
from pydantic import BaseModel

from policyengine.core import Output, Simulation
from policyengine.outputs.aggregate import (
    get_aggregate_variable,
    get_output_entity_data,
    require_output_column,
)

CountryCode = Literal["us", "uk"]
DecileValues = dict[int, float]

US_LSR_PARAMETER_PREFIXES = (
    "gov.simulation.labor_supply_responses.elasticities.income",
    "gov.simulation.labor_supply_responses.elasticities.substitution",
)
UK_LSR_PARAMETER_PREFIXES = (
    "gov.simulation.labour_supply_responses.income_elasticity",
    "gov.simulation.labour_supply_responses.substitution_elasticity",
    "gov.simulation.labor_supply_responses.income_elasticity",
    "gov.simulation.labor_supply_responses.substitution_elasticity",
)

US_ACTIVE_LSR_VARIABLES = {
    "person": [
        # Keep LSR-only support columns out of default household outputs.
        "self_employment_income",
        "weekly_hours_worked",
        "income_elasticity_lsr",
        "substitution_elasticity_lsr",
        "weekly_hours_worked_behavioural_response_income_elasticity",
        "weekly_hours_worked_behavioural_response_substitution_elasticity",
    ],
}
UK_ACTIVE_LSR_VARIABLES = {
    "person": [
        "income_elasticity_lsr",
        "substitution_elasticity_lsr",
    ],
}


class HoursResponse(BaseModel):
    baseline: float
    reform: float
    change: float
    income_effect: float
    substitution_effect: float


class LaborSupplyResponse(Output):
    substitution_lsr: float
    income_lsr: float
    relative_lsr: dict[str, float]
    total_change: float
    revenue_change: float
    decile: dict[str, dict[str, DecileValues]]
    hours: HoursResponse


def _parameter_name(value: Any) -> str | None:
    parameter = getattr(value, "parameter", None)
    return getattr(parameter, "name", None)


def _iter_reform_parameter_names(source: Any):
    if source is None:
        return
    if isinstance(source, Mapping):
        yield from (str(key) for key in source)
        return
    for parameter_value in getattr(source, "parameter_values", []) or []:
        name = _parameter_name(parameter_value)
        if name is not None:
            yield name


def _has_simulation_modifier(source: Any) -> bool:
    return getattr(source, "simulation_modifier", None) is not None


def _explicit_labor_supply_response_marker(source: Any) -> bool | None:
    return getattr(source, "affects_labor_supply_response", None)


def _labor_supply_parameter_prefixes(country_code: CountryCode) -> tuple[str, ...]:
    if country_code == "us":
        return US_LSR_PARAMETER_PREFIXES
    if country_code == "uk":
        return UK_LSR_PARAMETER_PREFIXES
    raise ValueError(
        f"Unsupported country_code for labor supply response: {country_code}"
    )


def _parameter_matches_labor_supply_response_prefix(
    parameter_name: str,
    prefixes: tuple[str, ...],
) -> bool:
    return any(
        parameter_name == prefix or parameter_name.startswith(f"{prefix}.")
        for prefix in prefixes
    )


def _simulation_may_have_labor_supply_response(
    simulation: Simulation,
    country_code: CountryCode,
) -> bool:
    prefixes = _labor_supply_parameter_prefixes(country_code)

    def source_may_have_labor_supply_response(source: Any) -> bool:
        if any(
            _parameter_matches_labor_supply_response_prefix(parameter_name, prefixes)
            for parameter_name in _iter_reform_parameter_names(source)
        ):
            return True

        explicit_marker = _explicit_labor_supply_response_marker(source)
        if explicit_marker is not None:
            return explicit_marker

        return _has_simulation_modifier(source)

    return any(
        source_may_have_labor_supply_response(source)
        for source in (simulation.policy, simulation.dynamic)
    )


def labor_supply_response_is_active(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    *,
    country_code: CountryCode,
) -> bool:
    """Return whether either scenario may produce non-zero LSR output."""
    return _simulation_may_have_labor_supply_response(
        baseline_simulation,
        country_code,
    ) or _simulation_may_have_labor_supply_response(
        reform_simulation,
        country_code,
    )


def _active_lsr_variables(country_code: CountryCode) -> dict[str, list[str]]:
    if country_code == "us":
        return US_ACTIVE_LSR_VARIABLES
    if country_code == "uk":
        return UK_ACTIVE_LSR_VARIABLES
    raise ValueError(
        f"Unsupported country_code for labor supply response: {country_code}"
    )


def _add_extra_variables(
    simulation: Simulation,
    variables_by_entity: dict[str, list[str]],
) -> None:
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


def configure_labor_supply_response_variables(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    *,
    country_code: CountryCode,
) -> bool:
    """Materialize expensive LSR columns only when a request needs them."""
    if not labor_supply_response_is_active(
        baseline_simulation,
        reform_simulation,
        country_code=country_code,
    ):
        return False

    active_variables = _active_lsr_variables(country_code)
    _add_extra_variables(baseline_simulation, active_variables)
    _add_extra_variables(reform_simulation, active_variables)
    return True


def _require_direct_output_column(
    simulation: Simulation,
    entity: str,
    column: str,
    context: str,
) -> None:
    data = get_output_entity_data(simulation, entity, context)
    if column in data.columns:
        return
    raise ValueError(
        f"{context} requires simulation '{simulation.id}' output data for "
        f"entity '{entity}' to include column '{column}'."
    )


def _has_direct_output_column(
    simulation: Simulation,
    entity: str,
    column: str,
) -> bool:
    data = get_output_entity_data(
        simulation,
        entity,
        f"LaborSupplyResponse.{entity}",
    )
    return column in data.columns


def _series_for_variable(
    simulation: Simulation,
    variable_name: str,
    target_entity: str,
    context: str,
) -> MicroSeries:
    variable = get_aggregate_variable(simulation, variable_name, context)
    target_data = get_output_entity_data(simulation, target_entity, context)

    if variable.entity != target_entity:
        source_data = get_output_entity_data(simulation, variable.entity, context)
        require_output_column(
            source_data,
            variable_name,
            variable.entity,
            simulation,
            context,
        )
        mapped = simulation.output_dataset.data.map_to_entity(
            variable.entity,
            target_entity,
            columns=[variable_name],
        )
        return mapped[variable_name]

    require_output_column(
        target_data,
        variable_name,
        target_entity,
        simulation,
        context,
    )
    return target_data[variable_name]


def _zero_household_series(baseline_simulation: Simulation) -> MicroSeries:
    household_data = get_output_entity_data(
        baseline_simulation,
        "household",
        "LaborSupplyResponse.household",
    )
    _require_direct_output_column(
        baseline_simulation,
        "household",
        "household_weight",
        "LaborSupplyResponse.household_weight",
    )
    return MicroSeries(
        [0.0] * len(household_data),
        weights=household_data["household_weight"].to_numpy(),
    )


def _positional_microseries(series: Any, weights: Any) -> MicroSeries:
    return MicroSeries(series.to_numpy(), weights=weights)


def _decile_values(series: MicroSeries) -> DecileValues:
    return {int(key): float(value) for key, value in series.to_dict().items()}


def _positive_decile_values(series: MicroSeries) -> DecileValues:
    return {
        int(key): float(value)
        for key, value in series.to_dict().items()
        if int(key) > 0
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def _positive_decile_ratios(
    numerators: MicroSeries,
    denominators: MicroSeries,
) -> DecileValues:
    numerator_values = numerators.to_dict()
    denominator_values = denominators.to_dict()
    return {
        int(key): _safe_ratio(float(numerator), float(denominator_values.get(key, 0.0)))
        for key, numerator in numerator_values.items()
        if int(key) > 0
    }


def _sum_variable(
    simulation: Simulation,
    variable_name: str,
    entity: str,
    context: str,
) -> float:
    return float(_series_for_variable(simulation, variable_name, entity, context).sum())


def _calculate_hours(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    *,
    country_code: CountryCode,
    active: bool,
) -> HoursResponse:
    if country_code != "us":
        return HoursResponse(
            baseline=0.0,
            reform=0.0,
            change=0.0,
            income_effect=0.0,
            substitution_effect=0.0,
        )

    if _has_direct_output_column(
        baseline_simulation,
        "person",
        "weekly_hours_worked",
    ) and _has_direct_output_column(
        reform_simulation,
        "person",
        "weekly_hours_worked",
    ):
        baseline_hours = _sum_variable(
            baseline_simulation,
            "weekly_hours_worked",
            "person",
            "LaborSupplyResponse.hours",
        )
        reform_hours = _sum_variable(
            reform_simulation,
            "weekly_hours_worked",
            "person",
            "LaborSupplyResponse.hours",
        )
    elif active:
        baseline_hours = _sum_variable(
            baseline_simulation,
            "weekly_hours_worked",
            "person",
            "LaborSupplyResponse.hours",
        )
        reform_hours = _sum_variable(
            reform_simulation,
            "weekly_hours_worked",
            "person",
            "LaborSupplyResponse.hours",
        )
    else:
        baseline_hours = 0.0
        reform_hours = 0.0

    if active:
        baseline_income_effect = _sum_variable(
            baseline_simulation,
            "weekly_hours_worked_behavioural_response_income_elasticity",
            "person",
            "LaborSupplyResponse.hours.income_effect",
        )
        reform_income_effect = _sum_variable(
            reform_simulation,
            "weekly_hours_worked_behavioural_response_income_elasticity",
            "person",
            "LaborSupplyResponse.hours.income_effect",
        )
        baseline_substitution_effect = _sum_variable(
            baseline_simulation,
            "weekly_hours_worked_behavioural_response_substitution_elasticity",
            "person",
            "LaborSupplyResponse.hours.substitution_effect",
        )
        reform_substitution_effect = _sum_variable(
            reform_simulation,
            "weekly_hours_worked_behavioural_response_substitution_elasticity",
            "person",
            "LaborSupplyResponse.hours.substitution_effect",
        )
    else:
        baseline_income_effect = 0.0
        reform_income_effect = 0.0
        baseline_substitution_effect = 0.0
        reform_substitution_effect = 0.0

    return HoursResponse(
        baseline=baseline_hours,
        reform=reform_hours,
        change=reform_hours - baseline_hours,
        income_effect=reform_income_effect - baseline_income_effect,
        substitution_effect=reform_substitution_effect - baseline_substitution_effect,
    )


def calculate_labor_supply_response(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    *,
    country_code: CountryCode,
) -> LaborSupplyResponse:
    """Calculate legacy macro labor-supply response output."""
    active = labor_supply_response_is_active(
        baseline_simulation,
        reform_simulation,
        country_code=country_code,
    )

    if active:
        baseline_income_lsr = _sum_variable(
            baseline_simulation,
            "income_elasticity_lsr",
            "person",
            "LaborSupplyResponse.income_lsr",
        )
        reform_income_lsr = _sum_variable(
            reform_simulation,
            "income_elasticity_lsr",
            "person",
            "LaborSupplyResponse.income_lsr",
        )
        baseline_substitution_lsr = _sum_variable(
            baseline_simulation,
            "substitution_elasticity_lsr",
            "person",
            "LaborSupplyResponse.substitution_lsr",
        )
        reform_substitution_lsr = _sum_variable(
            reform_simulation,
            "substitution_elasticity_lsr",
            "person",
            "LaborSupplyResponse.substitution_lsr",
        )

        income_lsr_hh = _series_for_variable(
            reform_simulation,
            "income_elasticity_lsr",
            "household",
            "LaborSupplyResponse.income_lsr_hh",
        ) - _series_for_variable(
            baseline_simulation,
            "income_elasticity_lsr",
            "household",
            "LaborSupplyResponse.income_lsr_hh",
        )
        substitution_lsr_hh = _series_for_variable(
            reform_simulation,
            "substitution_elasticity_lsr",
            "household",
            "LaborSupplyResponse.substitution_lsr_hh",
        ) - _series_for_variable(
            baseline_simulation,
            "substitution_elasticity_lsr",
            "household",
            "LaborSupplyResponse.substitution_lsr_hh",
        )
    else:
        baseline_income_lsr = 0.0
        reform_income_lsr = 0.0
        baseline_substitution_lsr = 0.0
        reform_substitution_lsr = 0.0
        income_lsr_hh = _zero_household_series(baseline_simulation)
        substitution_lsr_hh = _zero_household_series(baseline_simulation)

    income_lsr = reform_income_lsr - baseline_income_lsr
    substitution_lsr = reform_substitution_lsr - baseline_substitution_lsr
    total_change = substitution_lsr + income_lsr

    if not active:
        household_data = get_output_entity_data(
            baseline_simulation,
            "household",
            "LaborSupplyResponse.household",
        )
        _require_direct_output_column(
            baseline_simulation,
            "household",
            "household_income_decile",
            "LaborSupplyResponse.household_income_decile",
        )
        decile = household_data["household_income_decile"].to_numpy()
        zero_lsr_hh = _zero_household_series(baseline_simulation)
        decile_average = _decile_values(zero_lsr_hh.groupby(decile).mean())
        decile_relative = _positive_decile_values(zero_lsr_hh.groupby(decile).sum())

        return LaborSupplyResponse(
            substitution_lsr=0.0,
            income_lsr=0.0,
            relative_lsr={
                "income": 0.0,
                "substitution": 0.0,
            },
            total_change=0.0,
            # Legacy ``budgetary_impact_lsr`` was initialised to zero and not
            # recalculated, so preserve the effective public value.
            revenue_change=0.0,
            decile={
                "average": {
                    "income": decile_average,
                    "substitution": decile_average,
                },
                "relative": {
                    "income": decile_relative,
                    "substitution": decile_relative,
                },
            },
            hours=_calculate_hours(
                baseline_simulation,
                reform_simulation,
                country_code=country_code,
                active=False,
            ),
        )

    household_data = get_output_entity_data(
        baseline_simulation,
        "household",
        "LaborSupplyResponse.household",
    )
    _require_direct_output_column(
        baseline_simulation,
        "household",
        "household_income_decile",
        "LaborSupplyResponse.household_income_decile",
    )
    _require_direct_output_column(
        baseline_simulation,
        "household",
        "household_weight",
        "LaborSupplyResponse.household_weight",
    )
    decile = household_data["household_income_decile"].to_numpy()
    household_weight = household_data["household_weight"].to_numpy()

    employment_income_hh = _positional_microseries(
        _series_for_variable(
            baseline_simulation,
            "employment_income",
            "household",
            "LaborSupplyResponse.employment_income_hh",
        ),
        household_weight,
    )
    self_employment_income_hh = _positional_microseries(
        _series_for_variable(
            baseline_simulation,
            "self_employment_income",
            "household",
            "LaborSupplyResponse.self_employment_income_hh",
        ),
        household_weight,
    )

    income_lsr_hh = _positional_microseries(income_lsr_hh, household_weight)
    substitution_lsr_hh = _positional_microseries(
        substitution_lsr_hh,
        household_weight,
    )
    total_lsr_hh = MicroSeries(
        income_lsr_hh.to_numpy() + substitution_lsr_hh.to_numpy(),
        weights=household_weight,
    )
    original_earnings = MicroSeries(
        employment_income_hh.to_numpy()
        + self_employment_income_hh.to_numpy()
        - total_lsr_hh.to_numpy(),
        weights=household_weight,
    )

    decile_average = {
        "income": _decile_values(income_lsr_hh.groupby(decile).mean()),
        "substitution": _decile_values(substitution_lsr_hh.groupby(decile).mean()),
    }
    decile_relative = {
        "income": _positive_decile_ratios(
            income_lsr_hh.groupby(decile).sum(),
            original_earnings.groupby(decile).sum(),
        ),
        "substitution": _positive_decile_ratios(
            substitution_lsr_hh.groupby(decile).sum(),
            original_earnings.groupby(decile).sum(),
        ),
    }

    return LaborSupplyResponse(
        substitution_lsr=float(substitution_lsr),
        income_lsr=float(income_lsr),
        relative_lsr={
            "income": _safe_ratio(income_lsr_hh.sum(), original_earnings.sum()),
            "substitution": _safe_ratio(
                substitution_lsr_hh.sum(),
                original_earnings.sum(),
            ),
        },
        total_change=float(total_change),
        # Legacy ``budgetary_impact_lsr`` was initialised to zero and not
        # recalculated, so preserve the effective public value.
        revenue_change=0.0,
        decile={
            "average": decile_average,
            "relative": decile_relative,
        },
        hours=_calculate_hours(
            baseline_simulation,
            reform_simulation,
            country_code=country_code,
            active=active,
        ),
    )
