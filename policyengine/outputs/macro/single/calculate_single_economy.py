"""Calculate comparison statistics between two economic scenarios."""

import typing

from policyengine import Simulation

from pydantic import BaseModel

from .budget import FiscalSummary, _calculate_government_balance
from .inequality import InequalitySummary, _calculate_inequality
from typing import List


class SingleEconomy(BaseModel):
    fiscal: FiscalSummary
    """Government budgets and other top-level fiscal statistics."""
    inequality: InequalitySummary
    """Inequality statistics for the household sector."""


def calculate_single_economy(
    simulation: Simulation,
) -> SingleEconomy:
    """Calculate economy statistics for a single economic scenario."""
    options = simulation.options
    if simulation.is_comparison:
        raise ValueError(
            "This function is for single economy simulations only."
        )

    fiscal = _calculate_government_balance(
        simulation.baseline_simulation, options
    )
    inequality = _calculate_inequality(simulation.baseline_simulation)

    return SingleEconomy(
        fiscal=fiscal,
        inequality=inequality,
    )
