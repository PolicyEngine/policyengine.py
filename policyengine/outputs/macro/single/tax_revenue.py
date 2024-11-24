def tax_revenue(simulation):
    return simulation.baseline.calculate("gov_tax").sum() / 1e9
