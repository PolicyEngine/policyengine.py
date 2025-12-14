"""Tests for calculate_household_impact functions."""


from policyengine.tax_benefit_models.uk import (
    UKHouseholdInput,
    UKHouseholdOutput,
    uk_latest,
)
from policyengine.tax_benefit_models.uk import (
    calculate_household_impact as calculate_uk_household_impact,
)
from policyengine.tax_benefit_models.us import (
    USHouseholdInput,
    USHouseholdOutput,
    us_latest,
)
from policyengine.tax_benefit_models.us import (
    calculate_household_impact as calculate_us_household_impact,
)


class TestUKHouseholdImpact:
    """Tests for UK calculate_household_impact."""

    def test_single_adult_no_income(self):
        """Single adult with no income should have output for all entity variables."""
        household = UKHouseholdInput(
            people=[{"age": 30}],
            year=2026,
        )
        result = calculate_uk_household_impact(household)

        assert isinstance(result, UKHouseholdOutput)
        assert len(result.person) == 1
        assert len(result.benunit) == 1
        assert "hbai_household_net_income" in result.household

    def test_single_adult_with_employment_income(self):
        """Single adult with employment income should pay tax."""
        household = UKHouseholdInput(
            people=[{"age": 30, "employment_income": 50000}],
            year=2026,
        )
        result = calculate_uk_household_impact(household)

        assert isinstance(result, UKHouseholdOutput)
        assert result.person[0]["income_tax"] > 0
        assert result.person[0]["national_insurance"] > 0
        assert result.household["hbai_household_net_income"] > 0

    def test_family_with_children(self):
        """Family with children should receive child benefit."""
        household = UKHouseholdInput(
            people=[
                {"age": 35, "employment_income": 30000},
                {"age": 8},
                {"age": 5},
            ],
            benunit={"would_claim_child_benefit": True},
            year=2026,
        )
        result = calculate_uk_household_impact(household)

        assert isinstance(result, UKHouseholdOutput)
        assert len(result.person) == 3
        assert result.benunit[0]["child_benefit"] > 0

    def test_output_contains_all_entity_variables(self):
        """Output should contain all variables from entity_variables."""
        household = UKHouseholdInput(
            people=[{"age": 30, "employment_income": 25000}],
            year=2026,
        )
        result = calculate_uk_household_impact(household)

        # Check all household variables are present
        for var in uk_latest.entity_variables["household"]:
            assert var in result.household, (
                f"Missing household variable: {var}"
            )

        # Check all person variables are present
        for var in uk_latest.entity_variables["person"]:
            assert var in result.person[0], f"Missing person variable: {var}"

        # Check all benunit variables are present
        for var in uk_latest.entity_variables["benunit"]:
            assert var in result.benunit[0], f"Missing benunit variable: {var}"

    def test_output_is_json_serializable(self):
        """Output should be JSON serializable."""
        household = UKHouseholdInput(
            people=[{"age": 30, "employment_income": 25000}],
            year=2026,
        )
        result = calculate_uk_household_impact(household)

        json_dict = result.model_dump()
        assert isinstance(json_dict, dict)
        assert "household" in json_dict
        assert "person" in json_dict

    def test_input_is_json_serializable(self):
        """Input should be JSON serializable."""
        household = UKHouseholdInput(
            people=[{"age": 30, "employment_income": 25000}],
            year=2026,
        )

        json_dict = household.model_dump()
        assert isinstance(json_dict, dict)
        assert "people" in json_dict


class TestUSHouseholdImpact:
    """Tests for US calculate_household_impact."""

    def test_single_adult_no_income(self):
        """Single adult with no income."""
        household = USHouseholdInput(
            people=[{"age": 30, "is_tax_unit_head": True}],
            year=2024,
        )
        result = calculate_us_household_impact(household)

        assert isinstance(result, USHouseholdOutput)
        assert len(result.person) == 1
        assert "household_net_income" in result.household

    def test_single_adult_with_employment_income(self):
        """Single adult with employment income should pay tax."""
        household = USHouseholdInput(
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
        result = calculate_us_household_impact(household)

        assert isinstance(result, USHouseholdOutput)
        assert result.tax_unit[0]["income_tax"] > 0
        assert result.household["household_net_income"] > 0

    def test_output_contains_all_entity_variables(self):
        """Output should contain all variables from entity_variables."""
        household = USHouseholdInput(
            people=[
                {
                    "age": 30,
                    "employment_income": 25000,
                    "is_tax_unit_head": True,
                }
            ],
            year=2024,
        )
        result = calculate_us_household_impact(household)

        # Check all household variables are present
        for var in us_latest.entity_variables["household"]:
            assert var in result.household, (
                f"Missing household variable: {var}"
            )

        # Check all person variables are present
        for var in us_latest.entity_variables["person"]:
            assert var in result.person[0], f"Missing person variable: {var}"

    def test_output_is_json_serializable(self):
        """Output should be JSON serializable."""
        household = USHouseholdInput(
            people=[
                {
                    "age": 30,
                    "employment_income": 25000,
                    "is_tax_unit_head": True,
                }
            ],
            year=2024,
        )
        result = calculate_us_household_impact(household)

        json_dict = result.model_dump()
        assert isinstance(json_dict, dict)
        assert "household" in json_dict
        assert "person" in json_dict

    def test_input_is_json_serializable(self):
        """Input should be JSON serializable."""
        household = USHouseholdInput(
            people=[
                {
                    "age": 30,
                    "employment_income": 25000,
                    "is_tax_unit_head": True,
                }
            ],
            year=2024,
        )

        json_dict = household.model_dump()
        assert isinstance(json_dict, dict)
        assert "people" in json_dict
