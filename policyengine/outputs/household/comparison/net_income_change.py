def net_income_change(simulation):
    baseline_net_income = simulation.calculate("household/baseline/net_income")
    reform_net_income = simulation.calculate("household/reform/net_income")
    return reform_net_income - baseline_net_income
