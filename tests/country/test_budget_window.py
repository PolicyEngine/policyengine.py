

def test_budget_window():
    from policyengine import Simulation

    sim = Simulation(
        country="uk",
        scope="macro",
        reform={
            "gov.hmrc.income_tax.allowances.personal_allowance.amount": 10_000,
        },
    )

    window = sim.calculate_budget_window_comparison(count_years=3)

    assert len(window) == 3

    assert (window.federal_budget_impact > 0).all()
    assert window.federal_budget_impact.mean() > 15e9
