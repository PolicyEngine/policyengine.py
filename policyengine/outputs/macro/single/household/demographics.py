from policyengine import Simulation


def demographics(simulation: Simulation) -> dict:
    sim = simulation.selected
    household_count_people = (
        sim.calculate("household_count_people").astype(int).tolist()
    )
    person_weight = sim.calculate("person_weight").astype(float).tolist()
    household_weight = sim.calculate("household_weight").astype(float).tolist()
    is_male = sim.calculate("is_male").astype(bool).tolist()
    if "race" in sim.tax_benefit_system.variables:
        race = sim.calculate("race").astype(str).tolist()
    else:
        race = None
    age = sim.calculate("age").astype(int).tolist()
    return {
        "household_count_people": household_count_people,
        "person_weight": person_weight,
        "household_weight": household_weight,
        "is_male": is_male,
        "race": race,
        "age": age,
    }
