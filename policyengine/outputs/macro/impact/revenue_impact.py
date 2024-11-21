from policyengine import Simulation

def revenue_impact(simulation: Simulation):
    """Calculate the revenue impact of the given simulation.

    Args:
        simulation (Simulation): The simulation for which the revenue impact is to be calculated.

    Returns:
        float: The revenue impact of the simulation.
    """
    return simulation.reformed.calculate("household_tax").sum()/1e9 - simulation.baseline.calculate("household_tax").sum()/1e9