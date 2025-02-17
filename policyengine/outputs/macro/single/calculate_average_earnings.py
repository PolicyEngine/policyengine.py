from policyengine import PolicyEngine


def calculate_average_earnings(engine: PolicyEngine) -> float:
    """Calculate average earnings."""
    employment_income = simulation.baseline_simulation.calculate(
        "employment_income"
    )
    return employment_income[employment_income > 0].median()
