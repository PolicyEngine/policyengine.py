import plotly.express as px
import plotly.graph_objects as go
import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.charts import *
from .budget import create_budget_comparison_chart
from .budget_by_program import create_budget_program_comparison_chart
from .decile import create_decile_chart
from .winners_losers import create_winners_losers_chart
from .poverty import create_poverty_chart
from .inequality import create_inequality_chart
from .labor_supply import create_labor_supply_chart
from typing import Any


class MacroCharts(BaseModel):
    budget: Any
    budget_programs: Any
    decile_income_relative: Any
    decile_income_average: Any
    decile_wealth_relative: Any
    decile_wealth_average: Any
    winners_and_losers_income_decile: Any
    winners_and_losers_wealth_decile: Any


def create_all_charts(
    simulation: "Simulation",
) -> MacroCharts:
    """Create all charts."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")
    if not simulation.options.scope == "macro":
        raise ValueError(
            "This function is only available for macro simulations."
        )

    return MacroCharts(
        budget=create_budget_comparison_chart(simulation).to_dict(),
        budget_programs=create_budget_program_comparison_chart(
            simulation
        ).to_dict(),
        decile_income_relative=create_decile_chart(
            simulation, "income", True
        ).to_dict(),
        decile_income_average=create_decile_chart(
            simulation, "income", False
        ).to_dict(),
        decile_wealth_relative=create_decile_chart(
            simulation, "wealth", True
        ).to_dict(),
        decile_wealth_average=create_decile_chart(
            simulation, "wealth", True
        ).to_dict(),
        winners_and_losers_income_decile=create_winners_losers_chart(
            simulation, "income"
        ).to_dict(),
        winners_and_losers_wealth_decile=create_winners_losers_chart(
            simulation, "wealth"
        ).to_dict(),
    )
