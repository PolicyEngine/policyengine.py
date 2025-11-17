"""Tests for get_parameter and get_variable methods on TaxBenefitModelVersion."""

import pytest

from policyengine.tax_benefit_models.uk import uk_latest
from policyengine.tax_benefit_models.us import us_latest


def test_uk_get_variable():
    """Test getting a variable by name from UK model."""
    # Get a known variable
    var = uk_latest.get_variable("income_tax")

    assert var is not None
    assert var.name == "income_tax"
    assert var.entity == "person"
    assert var.tax_benefit_model_version == uk_latest


def test_uk_get_variable_not_found():
    """Test error handling when variable doesn't exist."""
    with pytest.raises(
        ValueError, match="Variable 'nonexistent_variable' not found"
    ):
        uk_latest.get_variable("nonexistent_variable")


def test_uk_get_parameter():
    """Test getting a parameter by name from UK model."""
    # Get a known parameter
    param = uk_latest.get_parameter(
        "gov.hmrc.income_tax.allowances.personal_allowance.amount"
    )

    assert param is not None
    assert (
        param.name
        == "gov.hmrc.income_tax.allowances.personal_allowance.amount"
    )
    assert param.tax_benefit_model_version == uk_latest


def test_uk_get_parameter_not_found():
    """Test error handling when parameter doesn't exist."""
    with pytest.raises(
        ValueError, match="Parameter 'nonexistent.parameter' not found"
    ):
        uk_latest.get_parameter("nonexistent.parameter")


def test_us_get_variable():
    """Test getting a variable by name from US model."""
    # Get a known variable
    var = us_latest.get_variable("income_tax")

    assert var is not None
    assert var.name == "income_tax"
    assert var.entity == "tax_unit"
    assert var.tax_benefit_model_version == us_latest


def test_us_get_variable_not_found():
    """Test error handling when variable doesn't exist."""
    with pytest.raises(
        ValueError, match="Variable 'nonexistent_variable' not found"
    ):
        us_latest.get_variable("nonexistent_variable")


def test_us_get_parameter():
    """Test getting a parameter by name from US model."""
    # Get a known parameter
    param = us_latest.get_parameter(
        "gov.irs.investment.net_investment_income_tax.rate"
    )

    assert param is not None
    assert param.name == "gov.irs.investment.net_investment_income_tax.rate"
    assert param.tax_benefit_model_version == us_latest


def test_us_get_parameter_not_found():
    """Test error handling when parameter doesn't exist."""
    with pytest.raises(
        ValueError, match="Parameter 'nonexistent.parameter' not found"
    ):
        us_latest.get_parameter("nonexistent.parameter")


def test_uk_multiple_variables():
    """Test getting multiple different variables."""
    vars_to_test = [
        "income_tax",
        "national_insurance",
        "universal_credit",
        "household_net_income",
    ]

    for var_name in vars_to_test:
        var = uk_latest.get_variable(var_name)
        assert var.name == var_name


def test_us_multiple_variables():
    """Test getting multiple different variables."""
    vars_to_test = [
        "income_tax",
        "employee_payroll_tax",
        "eitc",
        "household_net_income",
    ]

    for var_name in vars_to_test:
        var = us_latest.get_variable(var_name)
        assert var.name == var_name


def test_uk_multiple_parameters():
    """Test getting multiple different parameters."""
    params_to_test = [
        "gov.hmrc.income_tax.allowances.personal_allowance.amount",
        "gov.hmrc.income_tax.rates.uk[0].rate",
        "gov.dwp.universal_credit.means_test.reduction_rate",
    ]

    for param_name in params_to_test:
        param = uk_latest.get_parameter(param_name)
        assert param.name == param_name


def test_us_multiple_parameters():
    """Test getting multiple different parameters."""
    params_to_test = [
        "gov.irs.investment.net_investment_income_tax.rate",
        "gov.irs.self_employment.rate.social_security",
        "gov.irs.vita.eligibility.income_limit",
    ]

    for param_name in params_to_test:
        param = us_latest.get_parameter(param_name)
        assert param.name == param_name
