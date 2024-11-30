from policyengine import Simulation


def finance(simulation: Simulation) -> dict:
    sim = simulation.selected

    total_net_income = sim.calculate("household_net_income").sum()
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

    return {
        "total_net_income": total_net_income,
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
    }
