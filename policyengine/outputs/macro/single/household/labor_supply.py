from policyengine import Simulation


def labor_supply(simulation: Simulation, include_arrays: bool = False) -> dict:
    if not simulation.comparison:
        return {}
    sim = simulation.selected_sim
    household_count_people = sim.calculate("household_count_people").values
    result = {
        "substitution_lsr": 0,
        "income_lsr": 0,
        "income_lsr_hh": (household_count_people * 0).astype(float).tolist(),
        "substitution_lsr_hh": (household_count_people * 0)
        .astype(float)
        .tolist(),
        "weekly_hours": 0,
        "weekly_hours_income_effect": 0,
        "weekly_hours_substitution_effect": 0,
        "total_earnings": sim.calculate("employment_income").sum()
        + sim.calculate("self_employment_income").sum(),
        "total_workers": (sim.calculate("employment_income") > 0).sum()
        + (sim.calculate("self_employment_income") > 0).sum(),
    }

    if has_behavioral_response(simulation):
        result.update(
            {
                "substitution_lsr": sim.calculate(
                    "substitution_elasticity_lsr"
                ).sum(),
                "income_lsr": sim.calculate("income_elasticity_lsr").sum(),
                "income_lsr_hh": sim.calculate(
                    "income_elasticity_lsr", map_to="household"
                )
                .astype(float)
                .tolist(),
                "substitution_lsr_hh": sim.calculate(
                    "substitution_elasticity_lsr", map_to="household"
                )
                .astype(float)
                .tolist(),
            }
        )

        if simulation.country == "us":
            result.update(
                {
                    "weekly_hours": sim.calculate("weekly_hours_worked").sum(),
                    "weekly_hours_income_effect": sim.calculate(
                        "weekly_hours_worked_behavioural_response_income_elasticity"
                    ).sum(),
                    "weekly_hours_substitution_effect": sim.calculate(
                        "weekly_hours_worked_behavioural_response_substitution_elasticity"
                    ).sum(),
                }
            )

    if not include_arrays:
        return {
            key: value
            for key, value in result.items()
            if not isinstance(value, list)
        }
    else:
        return result


def has_behavioral_response(simulation):
    sim = simulation.selected_sim
    return (
        "employment_income_behavioral_response"
        in sim.tax_benefit_system.variables
        and any(sim.calculate("employment_income_behavioral_response") != 0)
    )
