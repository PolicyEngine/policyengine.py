def net_income(simulation):
    return simulation.selected_sim.calculate("household_net_income").sum()
