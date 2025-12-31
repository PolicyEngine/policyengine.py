"""Tests for UK and US tax-benefit model versions."""

import re

from policyengine.tax_benefit_models.uk import uk_latest
from policyengine.tax_benefit_models.us import us_latest


class TestUKModel:
    """Tests for PolicyEngine UK model."""

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
        assert (
            len(bracket_params_with_labels) > 0
        ), "Expected some bracket parameters to have generated labels"

    def test__given_bracket_label__then_follows_expected_format(self):
        """Bracket labels should follow the format 'Scale label (bracket N field)'."""
        for p in uk_latest.parameters:
            if "[" in p.name and p.label and "bracket" in p.label.lower():
                assert re.search(
                    r"\(bracket \d+ \w+\)", p.label
                ), f"Label '{p.label}' doesn't match expected bracket format"
                break


class TestUSModel:
    """Tests for PolicyEngine US model."""

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
        assert (
            len(breakdown_params_with_labels) > 0
        ), "Expected some breakdown parameters with SINGLE to have labels containing 'Single'"

    def test__given_bracket_parameter__then_has_generated_label(self):
        """Bracket parameters should have auto-generated labels."""
        bracket_params_with_labels = [
            p
            for p in us_latest.parameters
            if "[" in p.name and p.label and "bracket" in p.label.lower()
        ]
        assert (
            len(bracket_params_with_labels) > 0
        ), "Expected some bracket parameters to have generated labels"

    def test__given_breakdown_label__then_includes_enum_value_in_parentheses(
        self,
    ):
        """Generated breakdown labels should include the enum value in parentheses."""
        # Find a parameter with a generated label (contains both parent info and enum value)
        found = False
        for p in us_latest.parameters:
            if ".SINGLE" in p.name and p.label and "(" in p.label:
                assert (
                    "(Single)" in p.label
                ), f"Label '{p.label}' should contain '(Single)'"
                found = True
                break
        assert found, "Expected to find at least one generated breakdown label"

    def test__given_bracket_label__then_follows_expected_format(self):
        """Bracket labels should follow the format 'Scale label (bracket N field)'."""
        for p in us_latest.parameters:
            if "[0].rate" in p.name and p.label and "bracket" in p.label.lower():
                assert re.search(
                    r"\(bracket \d+ rate\)", p.label
                ), f"Label '{p.label}' doesn't match expected bracket format"
                break
