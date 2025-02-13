def test_uk_macro_single():
    from policyengine import Simulation

    sim = Simulation(
        scope="macro",
        country="uk",
    )

    sim.calculate_single_economy()


def test_uk_macro_comparison():
    from policyengine import Simulation

    sim = Simulation(
        scope="macro",
        country="uk",
        reform={
            "gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000,
        },
    )

    sim.calculate_economy_comparison()
