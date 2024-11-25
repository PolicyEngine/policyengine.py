from policyengine import Simulation


def demographic_values(simulation: Simulation) -> dict:
    sim = simulation.baseline
    household_count_people = (
        sim.calculate("household_count_people").astype(int).tolist()
    )
    person_weight = sim.calculate("person_weight").astype(float).tolist()
    household_weight = sim.calculate("household_weight").astype(float).tolist()
    return {
        "household_count_people": household_count_people,
        "person_weight": person_weight,
        "household_weight": household_weight,
    }
