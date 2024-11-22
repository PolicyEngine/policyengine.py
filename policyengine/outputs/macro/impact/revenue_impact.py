from policyengine import Simulation

def revenue_impact(simulation: Simulation):
    """Calculate the revenue impact of the given simulation.

    Args:
        simulation (Simulation): The simulation for which the revenue impact is to be calculated.

    Returns:
        float: The revenue impact of the simulation.
    """
    if simulation.country == "uk":
        return simulation.reformed.calculate("gov_balance").sum() - simulation.baseline.calculate("gov_balance").sum()