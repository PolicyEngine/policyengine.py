"""Calculate comparison statistics between two economic scenarios."""

import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.calculations import get_change
from policyengine_core.simulations import Simulation as CountrySimulation
from typing import Literal, List


class HouseholdComparison(BaseModel):
    household_net_income: float
    """The net income of the household."""


def calculate_net_income(
    baseline: CountrySimulation,
    reform: CountrySimulation,
) -> float:
    return (
        reform.calculate("household_net_income").sum()
        - baseline.calculate("household_net_income").sum()
    )


def calculate_household_comparison(
    simulation: "Simulation",
) -> HouseholdComparison:
    """Calculate comparison statistics between two household scenarios."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    baseline = simulation.baseline_simulation
    reform = simulation.reform_simulation

    net_income = calculate_net_income(baseline, reform)

    return HouseholdComparison(
        household_net_income=net_income,
    )
