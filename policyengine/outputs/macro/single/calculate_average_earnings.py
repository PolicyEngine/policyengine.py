from policyengine.simulation_results import MacroContext


def calculate_average_earnings(simulation: MacroContext) -> float:
    """Calculate average earnings."""
    employment_income = simulation.baseline_simulation.calculate(
        "employment_income"
    )
    return employment_income[employment_income > 0].median()
