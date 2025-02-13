"""Calculate comparison statistics between two economic scenarios."""

import typing

from policyengine import Simulation

from pydantic import BaseModel
from policyengine_core.simulations import Simulation as CountrySimulation
from typing import List, Dict
from datetime import date
from policyengine_core.variables import Variable
from policyengine_core.entities import Entity
from policyengine_core.model_api import YEAR, MONTH, ETERNITY, Enum
import dpath.util
import math
import json

Value = float | str | bool | list | None
Axes = List[List[Dict[str, str | int]]]
TimePeriodValues = Dict[str, Value]
EntityValues = Dict[str, TimePeriodValues]
EntityGroupValues = Dict[str, EntityValues]
FullHouseholdSpecification = Dict[
    str, EntityGroupValues | Axes
]  # {people: {person: {variable: {time_period: value}}}}


class SingleHousehold(BaseModel):
    """Statistics for a single household scenario."""

    full_household: FullHouseholdSpecification
    """Full variable calculations for the household."""


def calculate_single_household(
    simulation: Simulation,
) -> SingleHousehold:
    """Calculate household statistics for a single household scenario."""
    if simulation.is_comparison:
        raise ValueError(
            "This function is for single household simulations only."
        )

    return SingleHousehold(
        full_household=fill_and_calculate(
            simulation.options.data, simulation.baseline_simulation
        )
    )


def fill_and_calculate(
    household: FullHouseholdSpecification, simulation: CountrySimulation
):
    """Fill in missing variables and calculate all variables for a household"""
    # Copy the household to avoid modifying the original
    household = json.loads(json.dumps(household))
    household = add_yearly_variables(household, simulation)
    household = calculate_all_variables(household, simulation)
    household.pop("axes", None)
    return household


def get_requested_computations(
    household: FullHouseholdSpecification,
) -> List[tuple[str, str, str, str]]:
    requested_computations = dpath.util.search(
        {k: v for k, v in household.items() if k != "axes"},
        "*/*/*/*",
        # afilter=lambda t: t is None,
        yielded=True,
    )
    requested_computation_data = []

    for computation in requested_computations:
        path = computation[0]
        entity_plural, entity_id, variable_name, period = path.split("/")
        requested_computation_data.append(
            (entity_plural, entity_id, variable_name, period)
        )

    return requested_computation_data


def calculate_all_variables(
    household: FullHouseholdSpecification, simulation: CountrySimulation
) -> FullHouseholdSpecification:
    requested_computations = get_requested_computations(household)

    for (
        entity_plural,
        entity_id,
        variable_name,
        period,
    ) in requested_computations:
        variable = simulation.tax_benefit_system.get_variable(variable_name)
        result = simulation.calculate(variable_name, period)
        population = simulation.get_population(entity_plural)

        if "axes" in household:
            count_entities = len(household[entity_plural])
            entity_index = 0
            for _entity_id in household[entity_plural].keys():
                if _entity_id == entity_id:
                    break
                entity_index += 1
            try:
                result = result.astype(float)
            except:
                pass
            result = (
                result.reshape((-1, count_entities)).T[entity_index].tolist()
            )
            # If the result contains infinities, throw an error
            if any(
                [
                    not isinstance(value, str) and math.isinf(value)
                    for value in result
                ]
            ):
                raise ValueError("Infinite value")
            else:
                household[entity_plural][entity_id][variable_name][
                    period
                ] = result
        else:
            entity_index = population.get_index(entity_id)
            if variable.value_type == Enum:
                entity_result = result.decode()[entity_index].name
            elif variable.value_type == float:
                entity_result = float(str(result[entity_index]))
                # Convert infinities to JSON infinities
                if entity_result == float("inf"):
                    entity_result = "Infinity"
                elif entity_result == float("-inf"):
                    entity_result = "-Infinity"
            elif variable.value_type == str:
                entity_result = str(result[entity_index])
            else:
                entity_result = result.tolist()[entity_index]

            household[entity_plural][entity_id][variable_name][
                period
            ] = entity_result

    return household


def get_household_year(household: FullHouseholdSpecification) -> str:
    """Given a household dict, get the household's year

    Args:
        household (dict): The household itself
    """

    # Set household_year based on current year
    household_year = date.today().year

    # Determine if "age" variable present within household and return list of values at it
    household_age_list = list(
        household.get("people", {}).get("you", {}).get("age", {}).keys()
    )
    # If it is, overwrite household_year with the value present
    if len(household_age_list) > 0:
        household_year = household_age_list[0]

    return str(household_year)


def add_yearly_variables(
    household: FullHouseholdSpecification, simulation: CountrySimulation
) -> FullHouseholdSpecification:
    """
    Add yearly variables to a household dict before enqueueing calculation
    """

    variables: Dict[str, Variable] = simulation.tax_benefit_system.variables
    entities: Dict[str, Entity] = (
        simulation.tax_benefit_system.entities_by_singular()
    )
    household_year = get_household_year(household)

    for variable in variables:
        if variables[variable].definition_period in (YEAR, MONTH, ETERNITY):
            entity_plural = entities[variables[variable].entity.key].plural
            if entity_plural in household:
                possible_entities = household[entity_plural].keys()
                for entity in possible_entities:
                    if (
                        not variables[variable].name
                        in household[entity_plural][entity]
                    ):
                        if variables[variable].is_input_variable():
                            value = variables[variable].default_value
                            if isinstance(value, Enum):
                                value = value.name
                            household[entity_plural][entity][
                                variables[variable].name
                            ] = {household_year: value}
                        else:
                            household[entity_plural][entity][
                                variables[variable].name
                            ] = {household_year: None}
    return household
