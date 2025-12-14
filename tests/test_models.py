"""Tests for UK and US tax-benefit model versions."""


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
