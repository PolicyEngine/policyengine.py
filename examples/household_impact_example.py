"""Example: calculate tax and benefit outcomes for custom households.

Demonstrates the v4 :func:`policyengine.us.calculate_household` and
:func:`policyengine.uk.calculate_household` entry points. Both take flat
keyword arguments, accept reform dicts directly, and return a
:class:`~policyengine.tax_benefit_models.common.HouseholdResult` that
supports dot-access for scalar lookups.

Run: ``python examples/household_impact_example.py``
"""

from __future__ import annotations

import policyengine as pe


def uk_example() -> None:
    print("=" * 60)
    print("UK household calculator")
    print("=" * 60)

    # Single adult earning £50,000.
    single = pe.uk.calculate_household(
        people=[{"age": 35, "employment_income": 50_000}],
        year=2026,
    )
    print("\nSingle adult, £50k income:")
    print(f"  Net income:         £{single.household.hbai_household_net_income:,.0f}")
    print(f"  Income tax:         £{single.person[0].income_tax:,.0f}")
    print(f"  National Insurance: £{single.person[0].national_insurance:,.0f}")
    print(f"  Total tax:          £{single.household.household_tax:,.0f}")

    # Family with two children, £30k income, renting in the North West.
    family = pe.uk.calculate_household(
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
    print("\nFamily (2 adults, 2 children), £30k income, renting:")
    print(f"  Net income:       £{family.household.hbai_household_net_income:,.0f}")
    print(f"  Income tax:       £{family.person[0].income_tax:,.0f}")
    print(f"  Child benefit:    £{family.benunit.child_benefit:,.0f}")
    print(f"  Universal credit: £{family.benunit.universal_credit:,.0f}")
    print(f"  Total benefits:   £{family.household.household_benefits:,.0f}")


def us_example() -> None:
    print("\n" + "=" * 60)
    print("US household calculator")
    print("=" * 60)

    # Single adult earning $50,000 in California.
    single = pe.us.calculate_household(
        people=[{"age": 35, "employment_income": 50_000}],
        tax_unit={"filing_status": "SINGLE"},
        household={"state_code_str": "CA"},
        year=2026,
    )
    print("\nSingle adult, $50k income (California):")
    print(f"  Net income:  ${single.household.household_net_income:,.0f}")
    print(f"  Income tax:  ${single.tax_unit.income_tax:,.0f}")
    print(f"  Payroll tax: ${single.tax_unit.employee_payroll_tax:,.0f}")

    # Married couple with two kids, Texas, lower income.
    family = pe.us.calculate_household(
        people=[
            {"age": 35, "employment_income": 40_000},
            {"age": 33},
            {"age": 8},
            {"age": 5},
        ],
        tax_unit={"filing_status": "JOINT"},
        household={"state_code_str": "TX"},
        year=2026,
    )
    print("\nMarried couple with 2 children, $40k income (Texas):")
    print(f"  Net income:         ${family.household.household_net_income:,.0f}")
    print(f"  Federal income tax: ${family.tax_unit.income_tax:,.0f}")
    print(f"  EITC:               ${family.tax_unit.eitc:,.0f}")
    print(f"  Child tax credit:   ${family.tax_unit.ctc:,.0f}")
    print(f"  SNAP:               ${family.spm_unit.snap:,.0f}")


def main() -> None:
    uk_example()
    us_example()
    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
