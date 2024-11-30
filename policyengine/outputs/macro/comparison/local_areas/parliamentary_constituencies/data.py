from policyengine import Simulation


def data(simulation: Simulation) -> dict:
    if not simulation.options.get("include_constituencies"):
        return {}

    constituency_baseline = simulation.calculate(
        "macro/baseline/gov/local_areas/parliamentary_constituencies"
    )
    constituency_reform = simulation.calculate(
        "macro/reform/gov/local_areas/parliamentary_constituencies"
    )

    result = {}

    for constituency in constituency_baseline:
        result[constituency] = {}
        for key in constituency_baseline[constituency]:
            result[constituency][key] = {
                "change": constituency_reform[constituency][key]
                - constituency_baseline[constituency][key],
                "baseline": constituency_baseline[constituency][key],
                "reform": constituency_reform[constituency][key],
            }

    return result
