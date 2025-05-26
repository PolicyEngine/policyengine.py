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


def test_uk_macro_bad_package_versions_fail():
    from policyengine import Simulation

    try:
        sim = Simulation(
            scope="macro",
            country="uk",
            reform={
                "gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000,
            },
            model_version="a",
        )
        raise ValueError(
            "Simulation should have failed with a bad package version."
        )
    except:
        pass


def test_uk_macro_bad_data_version_fails():
    from policyengine import Simulation

    try:
        sim = Simulation(
            scope="macro",
            country="uk",
            reform={
                "gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000,
            },
            data_version="a",
        )
        raise ValueError(
            "Simulation should have failed with a bad data version."
        )
    except:
        pass
