"""Tests for US reform application via reform_dict at construction time.

These tests verify that the US model correctly applies reforms by building
a reform dict and passing it to Microsimulation at construction time,
fixing the p.update() bug that exists in the US country package.
"""


from policyengine.tax_benefit_models.us import (
    calculate_household_impact as calculate_us_household_impact,
)
from tests.fixtures.us_reform_fixtures import (
    DOUBLE_STANDARD_DEDUCTION_POLICY,
    HIGH_INCOME_SINGLE_FILER,
    MARRIED_COUPLE_WITH_KIDS,
    create_standard_deduction_policy,
)


class TestUSHouseholdReformApplication:
    """Tests for US household reform application."""

    def test__given_baseline_policy__then_returns_baseline_tax(self):
        """Given: No policy (baseline)
        When: Calculating household impact
        Then: Returns baseline tax calculation
        """
        # Given
        household = HIGH_INCOME_SINGLE_FILER

        # When
        result = calculate_us_household_impact(household, policy=None)

        # Then
        assert result.tax_unit[0]["income_tax"] > 0

    def test__given_doubled_standard_deduction__then_tax_is_lower(self):
        """Given: Policy that doubles standard deduction
        When: Calculating household impact
        Then: Income tax is lower than baseline
        """
        # Given
        household = HIGH_INCOME_SINGLE_FILER
        policy = DOUBLE_STANDARD_DEDUCTION_POLICY

        # When
        baseline_result = calculate_us_household_impact(household, policy=None)
        reform_result = calculate_us_household_impact(household, policy=policy)

        # Then
        baseline_tax = baseline_result.tax_unit[0]["income_tax"]
        reform_tax = reform_result.tax_unit[0]["income_tax"]

        assert reform_tax < baseline_tax, (
            f"Reform tax ({reform_tax}) should be less than baseline ({baseline_tax})"
        )

    def test__given_doubled_standard_deduction__then_tax_reduction_is_significant(
        self,
    ):
        """Given: Policy that doubles standard deduction
        When: Calculating household impact for high income household
        Then: Tax reduction is at least $1000 (significant impact)
        """
        # Given
        household = HIGH_INCOME_SINGLE_FILER
        policy = DOUBLE_STANDARD_DEDUCTION_POLICY

        # When
        baseline_result = calculate_us_household_impact(household, policy=None)
        reform_result = calculate_us_household_impact(household, policy=policy)

        # Then
        baseline_tax = baseline_result.tax_unit[0]["income_tax"]
        reform_tax = reform_result.tax_unit[0]["income_tax"]
        tax_reduction = baseline_tax - reform_tax

        assert tax_reduction >= 1000, (
            f"Tax reduction ({tax_reduction}) should be at least $1000"
        )

    def test__given_married_couple__then_joint_deduction_affects_tax(self):
        """Given: Married couple with doubled joint standard deduction
        When: Calculating household impact
        Then: Tax is lower than baseline
        """
        # Given
        household = MARRIED_COUPLE_WITH_KIDS
        policy = DOUBLE_STANDARD_DEDUCTION_POLICY

        # When
        baseline_result = calculate_us_household_impact(household, policy=None)
        reform_result = calculate_us_household_impact(household, policy=policy)

        # Then
        baseline_tax = baseline_result.tax_unit[0]["income_tax"]
        reform_tax = reform_result.tax_unit[0]["income_tax"]

        assert reform_tax < baseline_tax, (
            f"Reform tax ({reform_tax}) should be less than baseline ({baseline_tax})"
        )

    def test__given_same_policy_twice__then_results_are_deterministic(self):
        """Given: Same policy applied twice
        When: Calculating household impact
        Then: Results are identical (deterministic)
        """
        # Given
        household = HIGH_INCOME_SINGLE_FILER
        policy = DOUBLE_STANDARD_DEDUCTION_POLICY

        # When
        result1 = calculate_us_household_impact(household, policy=policy)
        result2 = calculate_us_household_impact(household, policy=policy)

        # Then
        assert result1.tax_unit[0]["income_tax"] == result2.tax_unit[0]["income_tax"]

    def test__given_custom_deduction_value__then_tax_reflects_value(self):
        """Given: Custom standard deduction value
        When: Calculating household impact
        Then: Tax reflects the custom deduction
        """
        # Given
        household = HIGH_INCOME_SINGLE_FILER

        # Create policies with different deduction values
        small_deduction_policy = create_standard_deduction_policy(
            single_value=5000, joint_value=10000
        )
        large_deduction_policy = create_standard_deduction_policy(
            single_value=50000, joint_value=100000
        )

        # When
        small_deduction_result = calculate_us_household_impact(
            household, policy=small_deduction_policy
        )
        large_deduction_result = calculate_us_household_impact(
            household, policy=large_deduction_policy
        )

        # Then
        small_tax = small_deduction_result.tax_unit[0]["income_tax"]
        large_tax = large_deduction_result.tax_unit[0]["income_tax"]

        assert large_tax < small_tax, (
            f"Large deduction tax ({large_tax}) should be less than small deduction ({small_tax})"
        )
