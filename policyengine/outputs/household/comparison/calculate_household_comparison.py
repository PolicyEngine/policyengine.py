"""Calculate comparison statistics between two economic scenarios."""

import typing

from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.calculations import get_change
from policyengine_core.simulations import Simulation as CountrySimulation
from policyengine.outputs.household.single.calculate_single_household import (
    SingleHousehold,
    fill_and_calculate,
    FullHouseholdSpecification,
)
from typing import Literal, List


class HouseholdComparison(BaseModel):
    full_household_baseline: FullHouseholdSpecification
    """The full completion of the household under the baseline scenario."""

    full_household_reform: FullHouseholdSpecification
    """The full completion of the household under the reform scenario."""

    change: FullHouseholdSpecification
    """The change in the household from the baseline to the reform scenario."""


def calculate_household_comparison(
    simulation: Simulation,
) -> HouseholdComparison:
    """Calculate comparison statistics between two household scenarios."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    baseline_household = fill_and_calculate(
        simulation.options.data, simulation.baseline_simulation
    )
    reform_household = fill_and_calculate(
        simulation.options.data, simulation.reform_simulation
    )
    change = get_change(
        baseline_household,
        reform_household,
        relative=False,
        skip_mismatch=True,
    )

    return HouseholdComparison(
        full_household_baseline=baseline_household,
        full_household_reform=reform_household,
        change=change,
    )
