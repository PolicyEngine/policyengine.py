"""Fixtures for US reform application tests."""

from datetime import date

import pytest

from policyengine.core import ParameterValue, Policy
from policyengine.tax_benefit_models.us import USHouseholdInput, us_latest


def create_standard_deduction_policy(
    single_value: float = 29200,
    joint_value: float = 58400,
    year: int = 2024,
) -> Policy:
    """Create a policy that sets standard deduction values."""
    std_deduction_single = us_latest.get_parameter(
        "gov.irs.deductions.standard.amount.SINGLE"
    )
    std_deduction_joint = us_latest.get_parameter(
        "gov.irs.deductions.standard.amount.JOINT"
    )

    return Policy(
        name=f"Standard Deduction: ${single_value:,.0f} single, ${joint_value:,.0f} joint",
        parameter_values=[
            ParameterValue(
                parameter=std_deduction_single,
                value=single_value,
                start_date=date(year, 1, 1),
            ),
            ParameterValue(
                parameter=std_deduction_joint,
                value=joint_value,
                start_date=date(year, 1, 1),
            ),
        ],
    )


# Pre-built policy fixtures

DOUBLE_STANDARD_DEDUCTION_POLICY = create_standard_deduction_policy(
    single_value=14600 * 2,  # Double from $14,600 to $29,200
    joint_value=29200 * 2,  # Double from $29,200 to $58,400
)

ZERO_STANDARD_DEDUCTION_POLICY = create_standard_deduction_policy(
    single_value=0,
    joint_value=0,
)

LARGE_STANDARD_DEDUCTION_POLICY = create_standard_deduction_policy(
    single_value=100000,
    joint_value=200000,
)


# Pre-built household fixtures

HIGH_INCOME_SINGLE_FILER = USHouseholdInput(
    people=[
        {
            "age": 35,
            "employment_income": 100000,
            "is_tax_unit_head": True,
        }
    ],
    tax_unit={"filing_status": "SINGLE"},
    year=2024,
)

MODERATE_INCOME_SINGLE_FILER = USHouseholdInput(
    people=[
        {
            "age": 30,
            "employment_income": 50000,
            "is_tax_unit_head": True,
        }
    ],
    tax_unit={"filing_status": "SINGLE"},
    year=2024,
)

MARRIED_COUPLE_WITH_KIDS = USHouseholdInput(
    people=[
        {"age": 40, "employment_income": 100000, "is_tax_unit_head": True},
        {"age": 38, "employment_income": 50000, "is_tax_unit_spouse": True},
        {"age": 10},
        {"age": 8},
    ],
    tax_unit={"filing_status": "JOINT"},
    year=2024,
)

LOW_INCOME_FAMILY = USHouseholdInput(
    people=[
        {"age": 28, "employment_income": 25000, "is_tax_unit_head": True},
        {"age": 5},
    ],
    tax_unit={"filing_status": "HEAD_OF_HOUSEHOLD"},
    year=2024,
)


# Pytest fixtures


@pytest.fixture
def double_standard_deduction_policy():
    """Pytest fixture for doubled standard deduction policy."""
    return DOUBLE_STANDARD_DEDUCTION_POLICY


@pytest.fixture
def high_income_single_filer():
    """Pytest fixture for high income single filer household."""
    return HIGH_INCOME_SINGLE_FILER


@pytest.fixture
def married_couple_with_kids():
    """Pytest fixture for married couple with kids household."""
    return MARRIED_COUPLE_WITH_KIDS
