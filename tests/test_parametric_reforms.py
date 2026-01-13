"""Test that parameter reforms are applied correctly."""

from datetime import datetime

from policyengine.core.policy import ParameterValue as PEParameterValue
from policyengine.core.policy import Policy as PEPolicy
from policyengine.tax_benefit_models.uk import uk_latest
from policyengine.tax_benefit_models.uk.analysis import (
    UKHouseholdInput,
    calculate_household_impact,
)


def test_parameter_reform_affects_calculation():
    """Test that modifying a parameter actually changes the calculation result."""
    param_lookup = {p.name: p for p in uk_latest.parameters}
    pe_param = param_lookup["gov.dwp.universal_credit.standard_allowance.amount.SINGLE_OLD"]

    pe_input = UKHouseholdInput(
        people=[{"age": 30, "employment_income": 0}],
        benunit={},
        household={},
        year=2026,
    )

    # Baseline
    baseline = calculate_household_impact(pe_input, policy=None)
    baseline_uc = baseline.benunit[0]["universal_credit"]

    # Reform - increase standard allowance
    pv = PEParameterValue(
        parameter=pe_param,
        value=533.0,
        start_date=datetime(2026, 1, 1),
        end_date=None,
    )
    policy = PEPolicy(name="Test", description="Test", parameter_values=[pv])
    reform = calculate_household_impact(pe_input, policy=policy)
    reform_uc = reform.benunit[0]["universal_credit"]

    # UC should increase
    assert reform_uc > baseline_uc
    assert abs(reform_uc - 533 * 12) < 1


def test_parameter_reform_preserves_inputs():
    """Test that input variables are preserved when applying a reform."""
    param_lookup = {p.name: p for p in uk_latest.parameters}
    pe_param = param_lookup["gov.dwp.universal_credit.standard_allowance.amount.SINGLE_OLD"]

    pe_input = UKHouseholdInput(
        people=[{"age": 30, "employment_income": 5000}],
        benunit={},
        household={},
        year=2026,
    )

    pv = PEParameterValue(
        parameter=pe_param,
        value=533.0,
        start_date=datetime(2026, 1, 1),
        end_date=None,
    )
    policy = PEPolicy(name="Test", description="Test", parameter_values=[pv])
    reform = calculate_household_impact(pe_input, policy=policy)

    assert reform.person[0]["employment_income"] == 5000
    assert reform.person[0]["age"] == 30
