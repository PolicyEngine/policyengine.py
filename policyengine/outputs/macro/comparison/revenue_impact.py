from policyengine import Simulation


def revenue_impact(simulation: Simulation):
    """Calculate the revenue impact of the given simulation.

    Args:
        simulation (Simulation): The simulation for which the revenue impact is to be calculated.

    Returns:
        float: The revenue impact of the simulation.
    """
    tax_revenue_baseline = simulation.calculate(
        "macro/baseline/gov/balance"
    )["total_tax_revenue"]
    tax_revenue_reform = simulation.calculate(
        "macro/reform/gov/balance"
    )["total_tax_revenue"]
    tax_revenue_impact = tax_revenue_reform - tax_revenue_baseline
    return {
        "tax_revenues": tax_revenue_impact,
    }
