"""Calculate comparison statistics between two economic scenarios."""

import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel

from .budget import FiscalSummary, calculate_government_balance
from .inequality import InequalitySummary, calculate_inequality
from .poverty import PovertyRateMetric, calculate_poverty
from typing import List


class SingleEconomy(BaseModel):
    fiscal: FiscalSummary
    """Government budgets and other top-level fiscal statistics."""
    inequality: InequalitySummary
    """Inequality statistics for the household sector."""
    poverty: List[PovertyRateMetric]
    """Poverty rates for different demographic groups and poverty definitions."""


def calculate_single_economy(
    simulation: "Simulation",
) -> SingleEconomy:
    """Calculate economy statistics for a single economic scenario."""
    options = simulation.options
    if simulation.is_comparison:
        raise ValueError(
            "This function is for single economy simulations only."
        )

    fiscal = calculate_government_balance(
        simulation.baseline_simulation, options
    )
    inequality = calculate_inequality(simulation.baseline_simulation)
    poverty = calculate_poverty(simulation.baseline_simulation, options)

    return SingleEconomy(
        fiscal=fiscal,
        inequality=inequality,
        poverty=poverty,
    )
