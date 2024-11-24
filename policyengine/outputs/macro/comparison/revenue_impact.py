from policyengine import Simulation


def revenue_impact(simulation: Simulation):
    """Calculate the revenue impact of the given simulation.

    Args:
        simulation (Simulation): The simulation for which the revenue impact is to be calculated.

    Returns:
        float: The revenue impact of the simulation.
    """
    tax_revenue_baseline = simulation.calculate("macro/baseline/tax_revenue")
    tax_revenue_reform = simulation.calculate("macro/reform/tax_revenue")
    return tax_revenue_reform - tax_revenue_baseline
