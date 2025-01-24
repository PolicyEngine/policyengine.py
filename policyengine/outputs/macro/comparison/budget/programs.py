import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation
from policyengine.outputs.macro.single import calculate_single_macro_scenario


def calculate_program_comparison(simulation: "Simulation"):
    """Calculate the detailed budgetary impact of the given simulation.

    Args:
        simulation (Simulation): The simulation for which the budgetary impact is to be calculated.

    Returns:
        dict: A dictionary containing the detailed budgetary impact for each program with the following keys:
            - baseline (float): The baseline budgetary impact of the program.
            - reform (float): The reform budgetary impact of the program.
            - difference (float): The difference between the reform and baseline budgetary impacts.
    """
    simulation.selected_sim = simulation.baseline_sim
    baseline = calculate_single_macro_scenario(simulation)
    simulation.selected_sim = simulation.reformed_sim
    reform = calculate_single_macro_scenario(simulation)
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
