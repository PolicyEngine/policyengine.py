def net_income(simulation):
    return simulation.baseline.calculate("household_net_income").sum()
