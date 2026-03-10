"""Fixtures for poverty-by-demographics convenience function tests.

These tests verify the delegation logic in calculate_*_poverty_by_age,
calculate_*_poverty_by_gender, and calculate_us_poverty_by_race. The
heavy lifting (actual poverty computation) is covered by test_poverty.py;
these fixtures mock the base poverty functions so we only test the
iteration, grouping, and filter_variable assignment.
"""

from unittest.mock import MagicMock

import pandas as pd

from policyengine.core import OutputCollection
from policyengine.outputs.poverty import (
    AGE_GROUPS,
    GENDER_GROUPS,
    RACE_GROUPS,
    UK_POVERTY_VARIABLES,
    US_POVERTY_VARIABLES,
    Poverty,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UK_POVERTY_TYPE_COUNT = len(UK_POVERTY_VARIABLES)  # 4
US_POVERTY_TYPE_COUNT = len(US_POVERTY_VARIABLES)  # 2

AGE_GROUP_COUNT = len(AGE_GROUPS)  # 3
GENDER_GROUP_COUNT = len(GENDER_GROUPS)  # 2
RACE_GROUP_COUNT = len(RACE_GROUPS)  # 4

AGE_GROUP_NAMES = list(AGE_GROUPS.keys())  # ["child", "adult", "senior"]
GENDER_GROUP_NAMES = list(GENDER_GROUPS.keys())  # ["male", "female"]
RACE_GROUP_NAMES = list(RACE_GROUPS.keys())  # ["white", "black", "hispanic", "other"]

EXPECTED_UK_BY_AGE_COUNT = AGE_GROUP_COUNT * UK_POVERTY_TYPE_COUNT  # 12
EXPECTED_US_BY_AGE_COUNT = AGE_GROUP_COUNT * US_POVERTY_TYPE_COUNT  # 6
EXPECTED_UK_BY_GENDER_COUNT = GENDER_GROUP_COUNT * UK_POVERTY_TYPE_COUNT  # 8
EXPECTED_US_BY_GENDER_COUNT = GENDER_GROUP_COUNT * US_POVERTY_TYPE_COUNT  # 4
EXPECTED_US_BY_RACE_COUNT = RACE_GROUP_COUNT * US_POVERTY_TYPE_COUNT  # 8


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def make_mock_simulation() -> MagicMock:
    """Create a minimal mock Simulation for Poverty constructor."""
    sim = MagicMock()
    sim.id = "mock-sim-id"
    return sim


def make_mock_poverty_outputs(
    simulation: MagicMock,
    poverty_variables: dict,
) -> list[Poverty]:
    """Create mock Poverty outputs matching the given poverty variable mapping.

    Each Poverty object has headcount, total_population, and rate set to
    predictable values so tests can verify the outputs are passed through
    correctly.
    """
    results = []
    for ptype, pvar in poverty_variables.items():
        p = MagicMock(spec=Poverty)
        p.simulation = simulation
        p.poverty_type = str(ptype)
        p.poverty_variable = pvar
        p.entity = "person"
        p.filter_variable = None
        p.headcount = 100.0
        p.total_population = 1000.0
        p.rate = 0.1
        results.append(p)
    return results


def make_mock_output_collection(
    outputs: list,
) -> OutputCollection:
    """Wrap mock outputs in an OutputCollection with a dummy DataFrame."""
    df = pd.DataFrame(
        [
            {
                "poverty_type": o.poverty_type,
                "headcount": o.headcount,
                "total_population": o.total_population,
                "rate": o.rate,
            }
            for o in outputs
        ]
    )
    return OutputCollection(outputs=outputs, dataframe=df)


def make_uk_mock_collection(simulation: MagicMock) -> OutputCollection:
    """Create an OutputCollection mimicking calculate_uk_poverty_rates output."""
    outputs = make_mock_poverty_outputs(simulation, UK_POVERTY_VARIABLES)
    return make_mock_output_collection(outputs)


def make_us_mock_collection(simulation: MagicMock) -> OutputCollection:
    """Create an OutputCollection mimicking calculate_us_poverty_rates output."""
    outputs = make_mock_poverty_outputs(simulation, US_POVERTY_VARIABLES)
    return make_mock_output_collection(outputs)
