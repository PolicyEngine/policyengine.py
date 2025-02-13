def test_us_macro_single():
    from policyengine import Simulation

    sim = Simulation(
        scope="macro",
        country="us",
    )

    sim.calculate_single_economy()


def test_us_macro_comparison():
    from policyengine import Simulation

    sim = Simulation(
        scope="macro",
        country="us",
        reform={
            "gov.usda.snap.income.deductions.earned_income": {"2025": 0.05}
        },
    )

    sim.calculate_economy_comparison()
