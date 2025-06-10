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


def test_us_macro_cliff_impacts():
    from policyengine import Simulation

    sim = Simulation(
        scope="macro",
        country="us",
        reform={
            "gov.usda.snap.income.deductions.earned_income": {"2025": 0.05}
        },
        include_cliffs=True,
    )

    result = sim.calculate_economy_comparison()
    cliff_impact = result.model_dump().get("cliff_impact")

    assert (
        cliff_impact is not None
    ), "Expected 'cliff_impact' to be present in the output."

    assert cliff_impact["baseline"]["cliff_gap"] > 0
    assert cliff_impact["reform"]["cliff_share"] > 0
