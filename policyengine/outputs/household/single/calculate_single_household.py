"""Calculate comparison statistics between two economic scenarios."""

import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine_core.simulations import Simulation as CountrySimulation
from typing import List


class SingleHousehold(BaseModel):
    household_net_income: float
    """The net income of the household."""


def calculate_net_income(
    simulation: CountrySimulation,
) -> float:
    return simulation.calculate("household_net_income").sum()


def calculate_single_household(
    simulation: "Simulation",
) -> SingleHousehold:
    """Calculate household statistics for a single household scenario."""
    if simulation.is_comparison:
        raise ValueError(
            "This function is for single economy simulations only."
        )

    net_income = calculate_net_income(simulation.baseline_simulation)

    return SingleHousehold(
        household_net_income=net_income,
    )
