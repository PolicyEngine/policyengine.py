"""Example: Calculate household tax and benefit impacts.

This script demonstrates using calculate_household_impact for both UK and US
to compute taxes and benefits for custom households.

Run: python examples/household_impact_example.py
"""

from policyengine.tax_benefit_models.uk import (
    UKHouseholdInput,
)
from policyengine.tax_benefit_models.uk import (
    calculate_household_impact as calculate_uk_impact,
)
from policyengine.tax_benefit_models.us import (
    USHouseholdInput,
)
from policyengine.tax_benefit_models.us import (
    calculate_household_impact as calculate_us_impact,
)


def uk_example():
    """UK household impact example."""
    print("=" * 60)
    print("UK HOUSEHOLD IMPACT")
    print("=" * 60)

    # Single adult earning £50,000
    household = UKHouseholdInput(
        people=[{"age": 35, "employment_income": 50_000}],
        year=2026,
    )
    result = calculate_uk_impact(household)

    print("\nSingle adult, £50k income:")
    print(
        f"  Net income: £{result.household['hbai_household_net_income']:,.0f}"
    )
    print(f"  Income tax: £{result.person[0]['income_tax']:,.0f}")
    print(
        f"  National Insurance: £{result.person[0]['national_insurance']:,.0f}"
    )
    print(f"  Total tax: £{result.household['household_tax']:,.0f}")

    # Family with two children, £30k income, renting
    household = UKHouseholdInput(
        people=[
            {"age": 35, "employment_income": 30_000},
            {"age": 33},
            {"age": 8},
            {"age": 5},
        ],
        benunit={
            "would_claim_uc": True,
            "would_claim_child_benefit": True,
        },
        household={
            "rent": 12_000,  # £1k/month
            "region": "NORTH_WEST",
        },
        year=2026,
    )
    result = calculate_uk_impact(household)

    print("\nFamily (2 adults, 2 children), £30k income, renting:")
    print(
        f"  Net income: £{result.household['hbai_household_net_income']:,.0f}"
    )
    print(f"  Income tax: £{result.person[0]['income_tax']:,.0f}")
    print(f"  Child benefit: £{result.benunit[0]['child_benefit']:,.0f}")
    print(f"  Universal credit: £{result.benunit[0]['universal_credit']:,.0f}")
    print(f"  Total benefits: £{result.household['household_benefits']:,.0f}")


def us_example():
    """US household impact example."""
    print("\n" + "=" * 60)
    print("US HOUSEHOLD IMPACT")
    print("=" * 60)

    # Single adult earning $50,000
    household = USHouseholdInput(
        people=[
            {"age": 35, "employment_income": 50_000, "is_tax_unit_head": True}
        ],
        tax_unit={"filing_status": "SINGLE"},
        household={"state_code_str": "CA"},
        year=2024,
    )
    result = calculate_us_impact(household)

    print("\nSingle adult, $50k income (California):")
    print(f"  Net income: ${result.household['household_net_income']:,.0f}")
    print(f"  Income tax: ${result.tax_unit[0]['income_tax']:,.0f}")
    print(f"  Payroll tax: ${result.tax_unit[0]['employee_payroll_tax']:,.0f}")

    # Married couple with children, lower income
    household = USHouseholdInput(
        people=[
            {"age": 35, "employment_income": 40_000, "is_tax_unit_head": True},
            {"age": 33, "is_tax_unit_spouse": True},
            {"age": 8, "is_tax_unit_dependent": True},
            {"age": 5, "is_tax_unit_dependent": True},
        ],
        tax_unit={"filing_status": "JOINT"},
        household={"state_code_str": "TX"},
        year=2024,
    )
    result = calculate_us_impact(household)

    print("\nMarried couple with 2 children, $40k income (Texas):")
    print(f"  Net income: ${result.household['household_net_income']:,.0f}")
    print(f"  Federal income tax: ${result.tax_unit[0]['income_tax']:,.0f}")
    print(f"  EITC: ${result.tax_unit[0]['eitc']:,.0f}")
    print(f"  Child tax credit: ${result.tax_unit[0]['ctc']:,.0f}")
    print(f"  SNAP: ${result.spm_unit[0]['snap']:,.0f}")


def main():
    uk_example()
    us_example()
    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
