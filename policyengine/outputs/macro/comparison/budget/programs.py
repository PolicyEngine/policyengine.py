from policyengine import Simulation


def programs(simulation: Simulation):
    """Calculate the detailed budgetary impact of the given simulation.

    Args:
        simulation (Simulation): The simulation for which the budgetary impact is to be calculated.

    Returns:
        dict: A dictionary containing the detailed budgetary impact for each program with the following keys:
            - baseline (float): The baseline budgetary impact of the program.
            - reform (float): The reform budgetary impact of the program.
            - difference (float): The difference between the reform and baseline budgetary impacts.
    """
    baseline = simulation.calculate("macro/baseline")
    reform = simulation.calculate("macro/reform")
    result = {}
    if simulation.country == "uk":
        for program in baseline["gov"]["programs"]:
            # baseline[programs][program] = total budgetary impact of program
            result[program] = dict(
                baseline=baseline["gov"]["programs"][program],
                reform=reform["gov"]["programs"][program],
                difference=reform["gov"]["programs"][program]
                - baseline["gov"]["programs"][program],
            )
    return result
