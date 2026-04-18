"""Tests for UK and US tax-benefit model versions and core models."""

import re

from policyengine.tax_benefit_models.uk import uk_latest
from policyengine.tax_benefit_models.us import us_latest


class TestUKModel:
    """Tests for PolicyEngine UK model."""

    def test_has_region_registry(self):
        """UK model should have a region registry attached."""
        assert uk_latest.region_registry is not None
        assert uk_latest.region_registry.country_id == "uk"

    def test_can_get_region_by_code(self):
        """UK model should be able to look up regions by code."""
        uk = uk_latest.get_region("uk")
        assert uk is not None
        assert uk.label == "United Kingdom"

        england = uk_latest.get_region("country/england")
        assert england is not None
        assert england.label == "England"

    def test_has_release_manifest_metadata(self):
        """UK model should expose its bundled release manifest metadata."""
        assert uk_latest.release_manifest is not None
        assert uk_latest.release_manifest.country_id == "uk"
        assert uk_latest.model_package.name == "policyengine-uk"
        assert uk_latest.model_package.version == "2.88.0"
        assert uk_latest.data_package.name == "policyengine-uk-data"
        assert uk_latest.data_package.version == "1.40.4"
        assert (
            uk_latest.default_dataset_uri
            == "hf://policyengine/policyengine-uk-data-private/enhanced_frs_2023_24.h5@1.40.4"
        )

    def test_has_hundreds_of_parameters(self):
        """UK model should have hundreds of parameters."""
        assert len(uk_latest.parameters) >= 100

    def test_has_hundreds_of_variables(self):
        """UK model should have hundreds of variables."""
        assert len(uk_latest.variables) >= 100

    def test_parameters_have_values(self):
        """Each parameter should have at least one parameter value."""
        total_values = 0
        for param in uk_latest.parameters[:100]:  # Check first 100 for speed
            values = param.parameter_values
            assert len(values) >= 1, f"Parameter {param.name} has no values"
            total_values += len(values)

        # Should have many parameter values in total
        assert total_values >= 100

    def test_parameter_values_have_required_fields(self):
        """Parameter values should have start_date and value."""
        for param in uk_latest.parameters[:50]:
            for pv in param.parameter_values:
                assert pv.start_date is not None
                assert pv.value is not None
                assert pv.parameter is param

    def test_model_version_parameter_values_aggregates_all(self):
        """model_version.parameter_values should aggregate all parameter values."""
        all_values = uk_latest.parameter_values
        assert len(all_values) >= 100

    def test__given_bracket_parameter__then_has_generated_label(self):
        """Bracket parameters should have auto-generated labels."""
        bracket_params_with_labels = [
            p
            for p in uk_latest.parameters
            if "[" in p.name and p.label and "bracket" in p.label.lower()
        ]
        assert len(bracket_params_with_labels) > 0, (
            "Expected some bracket parameters to have generated labels"
        )

    def test__given_bracket_label__then_follows_expected_format(self):
        """Bracket labels should follow the format 'Scale label (bracket N field)'."""
        for p in uk_latest.parameters:
            if "[" in p.name and p.label and "bracket" in p.label.lower():
                assert re.search(r"\(bracket \d+ \w+\)", p.label), (
                    f"Label '{p.label}' doesn't match expected bracket format"
                )
                break


class TestUSModel:
    """Tests for PolicyEngine US model."""

    def test_has_region_registry(self):
        """US model should have a region registry attached."""
        assert us_latest.region_registry is not None
        assert us_latest.region_registry.country_id == "us"

    def test_can_get_region_by_code(self):
        """US model should be able to look up regions by code."""
        us = us_latest.get_region("us")
        assert us is not None
        assert us.label == "United States"

        ca = us_latest.get_region("state/ca")
        assert ca is not None
        assert ca.label == "California"

    def test_has_release_manifest_metadata(self):
        """US model should expose its bundled release manifest metadata."""
        assert us_latest.release_manifest is not None
        assert us_latest.release_manifest.country_id == "us"
        assert us_latest.model_package.name == "policyengine-us"
        assert us_latest.model_package.version == "1.653.3"
        assert us_latest.data_package.name == "policyengine-us-data"
        assert us_latest.data_package.version == "1.73.0"
        assert (
            us_latest.default_dataset_uri
            == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.73.0"
        )

    def test_has_hundreds_of_parameters(self):
        """US model should have hundreds of parameters."""
        assert len(us_latest.parameters) >= 100

    def test_has_hundreds_of_variables(self):
        """US model should have hundreds of variables."""
        assert len(us_latest.variables) >= 100

    def test_parameters_have_values(self):
        """Each parameter should have at least one parameter value."""
        total_values = 0
        for param in us_latest.parameters[:100]:  # Check first 100 for speed
            values = param.parameter_values
            assert len(values) >= 1, f"Parameter {param.name} has no values"
            total_values += len(values)

        # Should have many parameter values in total
        assert total_values >= 100

    def test_parameter_values_have_required_fields(self):
        """Parameter values should have start_date and value."""
        for param in us_latest.parameters[:50]:
            for pv in param.parameter_values:
                assert pv.start_date is not None
                assert pv.value is not None
                assert pv.parameter is param

    def test_model_version_parameter_values_aggregates_all(self):
        """model_version.parameter_values should aggregate all parameter values."""
        all_values = us_latest.parameter_values
        assert len(all_values) >= 100

    def test__given_breakdown_parameter__then_has_generated_label(self):
        """Breakdown parameters (e.g., filing status) should have auto-generated labels."""
        breakdown_params_with_labels = [
            p
            for p in us_latest.parameters
            if ".SINGLE" in p.name and p.label and "Single" in p.label
        ]
        assert len(breakdown_params_with_labels) > 0, (
            "Expected some breakdown parameters with SINGLE to have labels containing 'Single'"
        )

    def test__given_bracket_parameter__then_has_generated_label(self):
        """Bracket parameters should have auto-generated labels."""
        bracket_params_with_labels = [
            p
            for p in us_latest.parameters
            if "[" in p.name and p.label and "bracket" in p.label.lower()
        ]
        assert len(bracket_params_with_labels) > 0, (
            "Expected some bracket parameters to have generated labels"
        )

    def test__given_breakdown_label__then_includes_enum_value_in_parentheses(
        self,
    ):
        """Generated breakdown labels should include the enum value in parentheses."""
        # Find a parameter with a generated label (contains both parent info and enum value)
        found = False
        for p in us_latest.parameters:
            if ".SINGLE" in p.name and p.label and "(" in p.label:
                assert "(Single)" in p.label, (
                    f"Label '{p.label}' should contain '(Single)'"
                )
                found = True
                break
        assert found, "Expected to find at least one generated breakdown label"

    def test__given_bracket_label__then_follows_expected_format(self):
        """Bracket labels should follow the format 'Scale label (bracket N field)'."""
        for p in us_latest.parameters:
            if "[0].rate" in p.name and p.label and "bracket" in p.label.lower():
                assert re.search(r"\(bracket \d+ rate\)", p.label), (
                    f"Label '{p.label}' doesn't match expected bracket format"
                )
                break


class TestVariableAddsSubtracts:
    """Tests for Variable adds/subtracts extraction and parameter path resolution."""

    def test_us_variable_with_list_adds_has_list(self):
        """US variables with list-type adds should have list[str] on the Variable."""
        # employment_income uses adds as a list of variable names
        var = next(
            (v for v in us_latest.variables if v.name == "employment_income"),
            None,
        )
        assert var is not None, "employment_income not found in US model"
        assert var.adds is not None, "employment_income should have adds"
        assert isinstance(var.adds, list), "adds should be a list"
        assert len(var.adds) > 0, "adds should not be empty"
        assert all(isinstance(name, str) for name in var.adds), (
            "all adds entries should be strings"
        )

    def test_us_variable_with_parameter_path_adds_resolves_to_list(self):
        """US variables whose core adds is a parameter path should resolve to list[str]."""
        # household_state_benefits uses adds as a parameter path string
        # "gov.household.household_state_benefits"
        var = next(
            (v for v in us_latest.variables if v.name == "household_state_benefits"),
            None,
        )
        assert var is not None, "household_state_benefits not found in US model"
        assert var.adds is not None, (
            "household_state_benefits should have adds (resolved from param path)"
        )
        assert isinstance(var.adds, list), (
            "adds should be resolved to a list, not a string"
        )
        assert len(var.adds) > 0, "resolved adds should not be empty"

    def test_us_variable_without_adds_has_none(self):
        """US variables without adds should have adds=None."""
        age_var = next((v for v in us_latest.variables if v.name == "age"), None)
        assert age_var is not None, "age variable not found in US model"
        assert age_var.adds is None, "age should not have adds"

    def test_us_variable_without_subtracts_has_none(self):
        """US variables without subtracts should have subtracts=None."""
        age_var = next((v for v in us_latest.variables if v.name == "age"), None)
        assert age_var is not None, "age variable not found in US model"
        assert age_var.subtracts is None, "age should not have subtracts"

    def test_us_some_variables_have_adds(self):
        """US model should have many variables with adds populated."""
        vars_with_adds = [v for v in us_latest.variables if v.adds is not None]
        assert len(vars_with_adds) >= 50, (
            f"Expected at least 50 variables with adds, got {len(vars_with_adds)}"
        )

    def test_uk_variable_with_adds_has_list(self):
        """UK variables with adds should have list[str] on the Variable."""
        # total_income is a common UK aggregation variable
        total_income_var = next(
            (v for v in uk_latest.variables if v.name == "total_income"), None
        )
        assert total_income_var is not None, "total_income not found in UK model"
        assert total_income_var.adds is not None, "total_income should have adds"
        assert isinstance(total_income_var.adds, list), "adds should be a list"
        assert len(total_income_var.adds) > 0, "adds should not be empty"

    def test_uk_variable_without_adds_has_none(self):
        """UK variables without adds should have adds=None."""
        age_var = next((v for v in uk_latest.variables if v.name == "age"), None)
        assert age_var is not None, "age variable not found in UK model"
        assert age_var.adds is None, "age should not have adds"

    def test_us_variable_with_subtracts_has_list(self):
        """US variables with subtracts should have list[str] on the Variable."""
        var = next(
            (v for v in us_latest.variables if v.name == "household_net_income"),
            None,
        )
        assert var is not None, "household_net_income not found in US model"
        assert var.subtracts is not None, "household_net_income should have subtracts"
        assert isinstance(var.subtracts, list), "subtracts should be a list"
        assert len(var.subtracts) > 0, "subtracts should not be empty"

    def test_adds_entries_are_valid_variable_names(self):
        """adds entries should reference real variable names in the model."""
        all_var_names = {v.name for v in us_latest.variables}
        var = next(
            (v for v in us_latest.variables if v.name == "employment_income"),
            None,
        )
        assert var is not None
        assert var.adds is not None
        for component_name in var.adds:
            assert component_name in all_var_names, (
                f"adds entry '{component_name}' is not a valid variable in the US model"
            )


class TestVariableDefaultValue:
    """Tests for Variable default_value and value_type fields."""

    def test_us_age_variable_has_default_value_40(self):
        """US age variable should have default_value of 40."""
        age_var = next((v for v in us_latest.variables if v.name == "age"), None)
        assert age_var is not None, "age variable not found in US model"
        assert age_var.default_value == 40, (
            f"Expected age default_value to be 40, got {age_var.default_value}"
        )

    def test_us_enum_variable_has_string_default_value(self):
        """Enum variables should have string default_value (not enum object)."""
        # age_group is an enum with default WORKING_AGE
        age_group_var = next(
            (v for v in us_latest.variables if v.name == "age_group"), None
        )
        assert age_group_var is not None, "age_group variable not found in US model"
        assert age_group_var.default_value == "WORKING_AGE", (
            f"Expected age_group default_value to be 'WORKING_AGE', "
            f"got {age_group_var.default_value}"
        )

    def test_us_variables_have_value_type(self):
        """US variables should have value_type set."""
        age_var = next((v for v in us_latest.variables if v.name == "age"), None)
        assert age_var is not None, "age variable not found in US model"
        assert age_var.value_type is not None, "age variable should have value_type"

    def test_uk_age_variable_has_default_value(self):
        """UK age variable should have default_value set."""
        age_var = next((v for v in uk_latest.variables if v.name == "age"), None)
        assert age_var is not None, "age variable not found in UK model"
        assert age_var.default_value is not None, "UK age should have default_value"
