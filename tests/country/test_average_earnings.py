def test_average_earnings():
    from policyengine import Simulation

    sim = Simulation(
        country="uk",
        scope="macro",
    )

    average_earnings = sim.calculate_average_earnings()

    assert (average_earnings < 50_000) and (average_earnings > 20_000)
