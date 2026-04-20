"""Tests for US reform dicts applied via ``pe.us.calculate_household``."""

import policyengine as pe
from tests.fixtures.us_reform_fixtures import (
    HIGH_INCOME_SINGLE_FILER,
    MARRIED_COUPLE_WITH_KIDS,
)


def _double_standard_deduction(year: int) -> dict:
    """Dict reform: standard deduction doubled from ~$14,600 / $29,200 baseline."""
    return {
        "gov.irs.deductions.standard.amount.SINGLE": {f"{year}-01-01": 29200},
        "gov.irs.deductions.standard.amount.JOINT": {f"{year}-01-01": 58400},
    }


class TestUSHouseholdReformApplication:
    def test__baseline__then_income_tax_positive(self):
        result = pe.us.calculate_household(**HIGH_INCOME_SINGLE_FILER)
        assert result.tax_unit.income_tax > 0

    def test__doubled_standard_deduction__then_tax_lower(self):
        baseline = pe.us.calculate_household(**HIGH_INCOME_SINGLE_FILER)
        reformed = pe.us.calculate_household(
            **HIGH_INCOME_SINGLE_FILER,
            reform=_double_standard_deduction(2024),
        )
        assert reformed.tax_unit.income_tax < baseline.tax_unit.income_tax

    def test__doubled_standard_deduction__then_reduction_is_meaningful(self):
        baseline = pe.us.calculate_household(**HIGH_INCOME_SINGLE_FILER)
        reformed = pe.us.calculate_household(
            **HIGH_INCOME_SINGLE_FILER,
            reform=_double_standard_deduction(2024),
        )
        reduction = baseline.tax_unit.income_tax - reformed.tax_unit.income_tax
        assert reduction >= 1000, (
            f"Tax reduction ({reduction}) should be at least $1000"
        )

    def test__married_couple_joint_deduction__then_tax_lower(self):
        baseline = pe.us.calculate_household(**MARRIED_COUPLE_WITH_KIDS)
        reformed = pe.us.calculate_household(
            **MARRIED_COUPLE_WITH_KIDS,
            reform=_double_standard_deduction(2024),
        )
        assert reformed.tax_unit.income_tax < baseline.tax_unit.income_tax

    def test__same_reform_twice__then_deterministic(self):
        reform = _double_standard_deduction(2024)
        first = pe.us.calculate_household(**HIGH_INCOME_SINGLE_FILER, reform=reform)
        second = pe.us.calculate_household(**HIGH_INCOME_SINGLE_FILER, reform=reform)
        assert first.tax_unit.income_tax == second.tax_unit.income_tax

    def test__custom_deduction_values__then_tax_reflects_values(self):
        small_reform = {
            "gov.irs.deductions.standard.amount.SINGLE": {"2024-01-01": 5000},
            "gov.irs.deductions.standard.amount.JOINT": {"2024-01-01": 10000},
        }
        large_reform = {
            "gov.irs.deductions.standard.amount.SINGLE": {"2024-01-01": 50000},
            "gov.irs.deductions.standard.amount.JOINT": {"2024-01-01": 100000},
        }
        small = pe.us.calculate_household(
            **HIGH_INCOME_SINGLE_FILER, reform=small_reform
        )
        large = pe.us.calculate_household(
            **HIGH_INCOME_SINGLE_FILER, reform=large_reform
        )
        assert large.tax_unit.income_tax < small.tax_unit.income_tax
