from policyengine import Simulation
from .income import calculate_income_decile_comparison
from .wealth import calculate_wealth_decile_comparison

def calculate_decile_comparison(
    simulation: Simulation,
) -> dict:    
    return {
        "income": calculate_income_decile_comparison(simulation),
        "wealth": calculate_wealth_decile_comparison(simulation),
    }