import pytest


def test_us_macro_single():
    """Test US macro single economy calculation using a state dataset.

    Uses Delaware (smallest state by population with data) to reduce memory
    usage in CI while still testing the full simulation pipeline.
    """
    from policyengine import Simulation

    sim = Simulation(
        scope="macro",
        country="us",
        region="state/DE",
    )

    sim.calculate_single_economy()


def test_us_macro_comparison():
    """Test US macro economy comparison using a state dataset.

    Uses Delaware (smallest state by population with data) to reduce memory
    usage in CI while still testing the full comparison pipeline.
    """
    from policyengine import Simulation

    sim = Simulation(
        scope="macro",
        country="us",
        region="state/DE",
        reform={
            "gov.usda.snap.income.deductions.earned_income": {"2025": 0.05}
        },
    )

    sim.calculate_economy_comparison()


@pytest.mark.skip(reason="Cliff calculations too slow with ECPS_2024 dataset")
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
