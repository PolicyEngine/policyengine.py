from typing import Optional, List
from pydantic import BaseModel, Field
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policyengine import Simulation

class SingleEconomyLaborSupply(BaseModel):
    substitution_lsr: float = Field(default=0, description="Substitution labor supply response")
    income_lsr: float = Field(default=0, description="Income labor supply response")
    income_lsr_hh: List[float] = Field(default_factory=list, description="Household income labor supply response")
    substitution_lsr_hh: List[float] = Field(default_factory=list, description="Household substitution labor supply response")
    weekly_hours: float = Field(default=0, description="Weekly hours worked")
    weekly_hours_income_effect: float = Field(default=0, description="Weekly hours worked income effect")
    weekly_hours_substitution_effect: float = Field(default=0, description="Weekly hours substitution effect")
    total_earnings: float = Field(..., description="Total employment and self-employment earnings")
    total_workers: int = Field(..., description="Total number of workers")


def has_behavioral_response(simulation: "Simulation") -> bool:
    """Check if simulation has behavioral responses."""
    sim = simulation.selected_sim
    return (
        "employment_income_behavioral_response" in sim.tax_benefit_system.variables
        and any(sim.calculate("employment_income_behavioral_response") != 0)
    )

def calculate_labor_supply(
    simulation: "Simulation", 
) -> SingleEconomyLaborSupply:
    """
    Calculate labor supply response metrics.
    
    Args:
        simulation (Simulation): Policy simulation object.
    
    Returns:
        SingleEconomyLaborSupply: Labor supply response metrics.
    """
    sim = simulation.selected_sim
    household_count_people = sim.calculate("household_count_people").values

    # Initialize base metrics
    labor_supply = SingleEconomyLaborSupply(
        income_lsr_hh=(household_count_people * 0).astype(float).tolist(),
        substitution_lsr_hh=(household_count_people * 0).astype(float).tolist(),
        total_earnings=sim.calculate("employment_income").sum() + 
                      sim.calculate("self_employment_income").sum(),
        total_workers=int((sim.calculate("employment_income") > 0).sum() + 
                     (sim.calculate("self_employment_income") > 0).sum()),
    )

    # Update behavioral response metrics if available
    if has_behavioral_response(simulation):
        labor_supply.substitution_lsr = sim.calculate("substitution_elasticity_lsr").sum()
        labor_supply.income_lsr = sim.calculate("income_elasticity_lsr").sum()
        labor_supply.income_lsr_hh = (
            sim.calculate("income_elasticity_lsr", map_to="household")
            .astype(float)
        )
        labor_supply.substitution_lsr_hh = (
            sim.calculate("substitution_elasticity_lsr", map_to="household")
            .astype(float)
        )

    # Update US-specific metrics
    if simulation.country == "us":
        labor_supply.weekly_hours = sim.calculate("weekly_hours_worked").sum()
        labor_supply.weekly_hours_income_effect = (
            sim.calculate("weekly_hours_worked_behavioural_response_income_elasticity")
            .sum()
        )
        labor_supply.weekly_hours_substitution_effect = (
            sim.calculate("weekly_hours_worked_behavioural_response_substitution_elasticity")
            .sum()
        )

    return labor_supply