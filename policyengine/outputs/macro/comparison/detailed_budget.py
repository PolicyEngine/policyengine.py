from policyengine import Simulation


def detailed_budget(simulation: Simulation):
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
