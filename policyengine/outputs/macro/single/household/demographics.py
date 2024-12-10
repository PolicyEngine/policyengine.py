from policyengine import Simulation


def demographics(simulation: Simulation, include_arrays: bool = False) -> dict:
    sim = simulation.selected_sim
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
    result = {
        "household_count_people": household_count_people,
        "person_weight": person_weight,
        "household_weight": household_weight,
        "total_households": sum(household_weight),
        "is_male": is_male,
        "age": age,
        "race": race,
    }
    if not include_arrays:
        return {
            "total_households": result["total_households"],
        }
    else:
        return result
