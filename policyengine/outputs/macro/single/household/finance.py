from policyengine import Simulation


def finance(simulation: Simulation, include_arrays: bool = False) -> dict:
    sim = simulation.selected_sim

    total_net_income = sim.calculate("household_net_income").sum()
    total_market_income = sim.calculate("household_market_income").sum()
    total_tax = sim.calculate("household_tax").sum()
    total_benefits = sim.calculate("household_benefits").sum()
    employment_income_hh = (
        sim.calculate("employment_income", map_to="household")
        .astype(float)
        .tolist()
    )
    self_employment_income_hh = (
        sim.calculate("self_employment_income", map_to="household")
        .astype(float)
        .tolist()
    )
    household_net_income = (
        sim.calculate("household_net_income").astype(float).tolist()
    )
    equiv_household_net_income = (
        sim.calculate("equiv_household_net_income").astype(float).tolist()
    )
    household_income_decile = (
        sim.calculate("household_income_decile").astype(int).tolist()
    )
    household_market_income = (
        sim.calculate("household_market_income").astype(float).tolist()
    )
    if "total_wealth" in sim.tax_benefit_system.variables:
        wealth = sim.calculate("total_wealth")
        household_count_people = sim.calculate("household_count_people").values
        wealth.weights *= household_count_people
        wealth_decile = wealth.decile_rank().clip(1, 10).astype(int).tolist()
        wealth = wealth.astype(float).tolist()
    else:
        wealth = None
        wealth_decile = None

    in_poverty = sim.calculate("in_poverty").astype(bool).tolist()
    person_in_poverty = (
        sim.calculate("in_poverty", map_to="person").astype(bool).tolist()
    )
    person_in_deep_poverty = (
        sim.calculate("in_deep_poverty", map_to="person").astype(bool).tolist()
    )
    poverty_gap = sim.calculate("poverty_gap").sum()
    deep_poverty_gap = sim.calculate("deep_poverty_gap").sum()

    poverty_rate = sim.calculate("in_poverty", map_to="person").mean()
    deep_poverty_rate = sim.calculate(
        "in_deep_poverty", map_to="person"
    ).mean()

    result = {
        "total_net_income": total_net_income,
        "total_market_income": total_market_income,
        "total_tax": total_tax,
        "total_benefits": total_benefits,
        "employment_income_hh": employment_income_hh,
        "self_employment_income_hh": self_employment_income_hh,
        "household_net_income": household_net_income,
        "equiv_household_net_income": equiv_household_net_income,
        "household_income_decile": household_income_decile,
        "household_market_income": household_market_income,
        "wealth": wealth,
        "wealth_decile": wealth_decile,
        "in_poverty": in_poverty,
        "person_in_poverty": person_in_poverty,
        "person_in_deep_poverty": person_in_deep_poverty,
        "poverty_gap": poverty_gap,
        "deep_poverty_gap": deep_poverty_gap,
        "poverty_rate": poverty_rate,
        "deep_poverty_rate": deep_poverty_rate,
    }

    if not include_arrays:
        return {
            key: value
            for key, value in result.items()
            if not isinstance(value, list)
        }
    else:
        return result
