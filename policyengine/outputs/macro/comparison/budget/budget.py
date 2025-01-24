from policyengine import Simulation
from .breakdown import calculate_provision_breakdown_comparison
from .general import calculate_general_budget_comparison
from .window import calculate_budget_window_comparison
from .programs import calculate_program_comparison

def calculate_budget_comparison(
    simulation: Simulation,
) -> dict:    
    return {
        "breakdown": calculate_provision_breakdown_comparison(simulation),
        "general": calculate_general_budget_comparison(simulation),
        "window": calculate_budget_window_comparison(simulation),
        "programs": calculate_program_comparison(simulation
    }