def calculate_net_income(simulation) -> float:
    return simulation.selected_sim.calculate("household_net_income").sum()
