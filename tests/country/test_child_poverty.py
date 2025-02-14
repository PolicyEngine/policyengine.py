def test_child_poverty():
    from policyengine import Simulation

    sim = Simulation(
        country="us",
        scope="macro",
        reform={
            "gov.irs.credits.ctc.refundable.fully_refundable": True,
        },
    )

    child_poverty = sim.calculate_child_poverty_impacts(count_years=3)

    assert len(child_poverty) == 3

    assert (child_poverty.child_poverty_change < 0).all()
    assert child_poverty.reform_child_poverty > 0
    assert child_poverty.baseline_child_poverty > 0
