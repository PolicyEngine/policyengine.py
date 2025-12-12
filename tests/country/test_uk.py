import pytest


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

    with pytest.raises(ValueError):
        Simulation(
            scope="macro",
            country="uk",
            reform={
                "gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000,
            },
            model_version="a",
        )


def test_uk_macro_bad_data_version_fails():
    from policyengine import Simulation

    with pytest.raises(ValueError):
        Simulation(
            scope="macro",
            country="uk",
            reform={
                "gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000,
            },
            data_version="a",
        )


def test_uk_macro_comparison_has_local_authority_impact():
    """Test that UK macro comparison includes local authority breakdown."""
    from policyengine import Simulation

    sim = Simulation(
        scope="macro",
        country="uk",
        reform={
            "gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000,
        },
    )

    result = sim.calculate_economy_comparison()

    # Check local_authority_impact is present and not None for UK
    assert hasattr(result, "local_authority_impact")
    assert result.local_authority_impact is not None

    # Check structure
    la_impact = result.local_authority_impact
    assert hasattr(la_impact, "by_local_authority")
    assert len(la_impact.by_local_authority) > 0

    # Check each local authority has required fields
    for name, data in la_impact.by_local_authority.items():
        assert hasattr(data, "average_household_income_change")
        assert hasattr(data, "relative_household_income_change")
        assert hasattr(data, "x")
        assert hasattr(data, "y")
        assert isinstance(data.average_household_income_change, float)
        assert isinstance(data.relative_household_income_change, float)
        assert isinstance(data.x, int)
        assert isinstance(data.y, int)


def test_uk_macro_comparison_constituency_and_local_authority_both_present():
    """Test that both constituency and local authority impacts are present."""
    from policyengine import Simulation

    sim = Simulation(
        scope="macro",
        country="uk",
        reform={
            "gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000,
        },
    )

    result = sim.calculate_economy_comparison()

    # Both should be present for UK
    assert result.constituency_impact is not None
    assert result.local_authority_impact is not None

    # Constituencies should have outcomes_by_region, local authorities should not
    assert hasattr(result.constituency_impact, "outcomes_by_region")
    assert not hasattr(result.local_authority_impact, "outcomes_by_region")


def test_uk_simulation_local_authority_region_filter_by_code():
    """Test that simulation can filter by local authority code."""
    from policyengine import Simulation

    # Use a known local authority code (Westminster)
    sim = Simulation(
        scope="macro",
        country="uk",
        region="local_authority/E09000033",
    )

    # Should not raise an error
    result = sim.calculate_single_economy()
    assert result is not None


def test_uk_simulation_local_authority_region_filter_by_name():
    """Test that simulation can filter by local authority name."""
    from policyengine import Simulation

    # Use a known local authority name
    sim = Simulation(
        scope="macro",
        country="uk",
        region="local_authority/Westminster",
    )

    # Should not raise an error
    result = sim.calculate_single_economy()
    assert result is not None


def test_uk_simulation_invalid_local_authority_raises_error():
    """Test that invalid local authority raises ValueError."""
    from policyengine import Simulation

    with pytest.raises(ValueError, match="Local authority .* not found"):
        Simulation(
            scope="macro",
            country="uk",
            region="local_authority/InvalidLocalAuthority123",
        )
