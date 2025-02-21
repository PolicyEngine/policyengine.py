from policyengine.model_api import *
import dpath.util
import math
from policyengine_core.enums import Enum
import logging
import numpy as np


def calculate_household(
    household: dict,
    country: str,
    policy: Policy = current_law,
    verbose: bool = False,
) -> dict:
    household = json.loads(json.dumps(household))
    requested_computations = get_requested_computations(household)

    logger = logging.getLogger()
    if verbose:
        logger.setLevel(logging.INFO)
    
    simulation = Simulation(
        country=country,
        policy=policy,
        dataset=Dataset(situation=household),
        calculations=[
            (variable_name, period)
            for (
                _,
                _,
                variable_name,
                period,
            ) in requested_computations
        ],
    )

    simulation.compute()

    simulation.trace = True

    for (
        entity_plural,
        entity_id,
        variable_name,
        period,
    ) in requested_computations:
        try:
            variable = simulation.simulation.tax_benefit_system.get_variable(variable_name)
            result: np.ndarray = simulation.simulation.calculate(variable_name, period)
            population = simulation.simulation.get_population(entity_plural)

            if "axes" in household:
                count_entities = len(household[entity_plural])
                entity_index = 0
                for _entity_id in household[entity_plural].keys():
                    if _entity_id == entity_id:
                        break
                    entity_index += 1
                result = (
                    result.astype(float)
                    .reshape((-1, count_entities))
                    .T[entity_index]
                    .tolist()
                )
                # If the result contains infinities, throw an error
                if any([math.isinf(value) for value in result]):
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
        except Exception as e:
            if "axes" in household:
                pass
            else:
                household[entity_plural][entity_id][variable_name][
                    period
                ] = None
            logging.warning(
                f"Error computing {variable_name} for {entity_id}: {e}"
            )
    
    return household

def get_requested_computations(household: dict):
    requested_computations = dpath.util.search(
        household,
        "*/*/*/*",
        afilter=lambda t: t is None,
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