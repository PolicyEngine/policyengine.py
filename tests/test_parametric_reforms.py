"""Tests for parametric reforms utility functions."""

from datetime import date, datetime
from unittest.mock import MagicMock

from policyengine.utils.parametric_reforms import (
    reform_dict_from_parameter_values,
    simulation_modifier_from_parameter_values,
)
from tests.fixtures.parametric_reforms_fixtures import (
    MOCK_PARAM_JOINT,
    MOCK_PARAM_SINGLE,
    MOCK_PARAM_TAX_RATE,
    MULTI_PERIOD_PARAM_VALUES,
    MULTIPLE_DIFFERENT_PARAMS,
    PARAM_VALUE_WITH_END_DATE,
    SINGLE_PARAM_VALUE,
    create_mock_parameter,
    create_parameter_value,
)


class TestReformDictFromParameterValues:
    """Tests for the reform_dict_from_parameter_values function."""

    def test__given_none_parameter_values__then_returns_none(self):
        """Given: None as parameter_values
        When: Calling reform_dict_from_parameter_values
        Then: Returns None
        """
        # Given
        parameter_values = None

        # When
        result = reform_dict_from_parameter_values(parameter_values)

        # Then
        assert result is None

    def test__given_empty_list__then_returns_none(self):
        """Given: Empty list of parameter values
        When: Calling reform_dict_from_parameter_values
        Then: Returns None
        """
        # Given
        parameter_values = []

        # When
        result = reform_dict_from_parameter_values(parameter_values)

        # Then
        assert result is None

    def test__given_single_parameter_value__then_returns_dict_with_one_entry(
        self,
    ):
        """Given: Single parameter value
        When: Calling reform_dict_from_parameter_values
        Then: Returns dict with parameter name and period-value mapping
        """
        # Given
        pv = SINGLE_PARAM_VALUE

        # When
        result = reform_dict_from_parameter_values([pv])

        # Then
        assert result is not None
        assert MOCK_PARAM_SINGLE.name in result
        assert "2024-01-01" in result[MOCK_PARAM_SINGLE.name]
        assert result[MOCK_PARAM_SINGLE.name]["2024-01-01"] == 29200

    def test__given_parameter_value_with_end_date__then_uses_period_range_format(
        self,
    ):
        """Given: Parameter value with start_date and end_date
        When: Calling reform_dict_from_parameter_values
        Then: Returns dict with period range format "start.end"
        """
        # Given
        pv = PARAM_VALUE_WITH_END_DATE

        # When
        result = reform_dict_from_parameter_values([pv])

        # Then
        assert result is not None
        param_name = MOCK_PARAM_SINGLE.name
        assert param_name in result
        # Should use "start.end" format
        assert "2024-01-01.2024-12-31" in result[param_name]
        assert result[param_name]["2024-01-01.2024-12-31"] == 29200

    def test__given_multiple_periods_same_parameter__then_includes_all_periods(
        self,
    ):
        """Given: Multiple parameter values for same parameter (different periods)
        When: Calling reform_dict_from_parameter_values
        Then: Returns dict with all periods for that parameter
        """
        # Given
        param_values = MULTI_PERIOD_PARAM_VALUES

        # When
        result = reform_dict_from_parameter_values(param_values)

        # Then
        assert result is not None
        param_name = MOCK_PARAM_SINGLE.name
        assert param_name in result
        assert len(result[param_name]) == 2
        assert result[param_name]["2024-01-01"] == 29200
        assert result[param_name]["2025-01-01"] == 30000

    def test__given_multiple_different_parameters__then_includes_all_parameters(
        self,
    ):
        """Given: Multiple parameter values for different parameters
        When: Calling reform_dict_from_parameter_values
        Then: Returns dict with all parameters
        """
        # Given
        param_values = MULTIPLE_DIFFERENT_PARAMS

        # When
        result = reform_dict_from_parameter_values(param_values)

        # Then
        assert result is not None
        assert len(result) == 3
        assert MOCK_PARAM_SINGLE.name in result
        assert MOCK_PARAM_JOINT.name in result
        assert MOCK_PARAM_TAX_RATE.name in result
        assert result[MOCK_PARAM_SINGLE.name]["2024-01-01"] == 29200
        assert result[MOCK_PARAM_JOINT.name]["2024-01-01"] == 58400
        assert result[MOCK_PARAM_TAX_RATE.name]["2024-01-01"] == 0.10

    def test__given_parameter_value__then_preserves_value_type(self):
        """Given: Parameter values with different types (int, float)
        When: Calling reform_dict_from_parameter_values
        Then: Values preserve their original types
        """
        # Given
        mock_param = create_mock_parameter("gov.test.rate")
        pv_float = create_parameter_value(
            parameter=mock_param,
            value=0.15,
            start_date=date(2024, 1, 1),
        )

        # When
        result = reform_dict_from_parameter_values([pv_float])

        # Then
        assert result["gov.test.rate"]["2024-01-01"] == 0.15
        assert isinstance(result["gov.test.rate"]["2024-01-01"], float)


class TestSimulationModifierFromParameterValues:
    """Tests for the simulation_modifier_from_parameter_values function."""

    def test__given_empty_list__then_returns_callable(self):
        """Given: Empty list of parameter values
        When: Calling simulation_modifier_from_parameter_values
        Then: Returns a callable function
        """
        # Given
        parameter_values = []

        # When
        result = simulation_modifier_from_parameter_values(parameter_values)

        # Then
        assert callable(result)

    def test__given_parameter_values__then_returns_modifier_function(self):
        """Given: List of parameter values
        When: Calling simulation_modifier_from_parameter_values
        Then: Returns a callable modifier function
        """
        # Given
        param_values = [SINGLE_PARAM_VALUE]

        # When
        result = simulation_modifier_from_parameter_values(param_values)

        # Then
        assert callable(result)

    def test__given_modifier__then_calls_p_update_for_each_value(self):
        """Given: Modifier function from parameter values
        When: Calling the modifier with a mock simulation
        Then: Calls p.update() for each parameter value
        """
        # Given
        mock_simulation = MagicMock()
        mock_param_node = MagicMock()
        mock_simulation.tax_benefit_system.parameters.get_child.return_value = (
            mock_param_node
        )

        param_values = [SINGLE_PARAM_VALUE]
        modifier = simulation_modifier_from_parameter_values(param_values)

        # When
        modifier(mock_simulation)

        # Then
        mock_simulation.tax_benefit_system.parameters.get_child.assert_called_once_with(
            MOCK_PARAM_SINGLE.name
        )
        mock_param_node.update.assert_called_once()

    def test__given_multiple_values__then_applies_all_updates(self):
        """Given: Multiple parameter values
        When: Calling the modifier with a mock simulation
        Then: Applies updates for all parameter values
        """
        # Given
        mock_simulation = MagicMock()
        mock_param_node = MagicMock()
        mock_simulation.tax_benefit_system.parameters.get_child.return_value = (
            mock_param_node
        )

        param_values = MULTIPLE_DIFFERENT_PARAMS
        modifier = simulation_modifier_from_parameter_values(param_values)

        # When
        modifier(mock_simulation)

        # Then
        assert (
            mock_simulation.tax_benefit_system.parameters.get_child.call_count
            == 3
        )
        assert mock_param_node.update.call_count == 3

    def test__given_modifier__then_returns_simulation(self):
        """Given: Modifier function
        When: Calling with a simulation
        Then: Returns the simulation object
        """
        # Given
        mock_simulation = MagicMock()
        mock_param_node = MagicMock()
        mock_simulation.tax_benefit_system.parameters.get_child.return_value = (
            mock_param_node
        )

        modifier = simulation_modifier_from_parameter_values([SINGLE_PARAM_VALUE])

        # When
        result = modifier(mock_simulation)

        # Then
        assert result is mock_simulation

    def test__given_modifier__then_clears_parameter_caches(self):
        """Given: Modifier function
        When: Calling with a simulation
        Then: Clears parameter caches on the tax benefit system
        """
        # Given
        mock_simulation = MagicMock()
        mock_param_node = MagicMock()
        mock_simulation.tax_benefit_system.parameters.get_child.return_value = (
            mock_param_node
        )

        modifier = simulation_modifier_from_parameter_values([SINGLE_PARAM_VALUE])

        # When
        modifier(mock_simulation)

        # Then
        mock_simulation.tax_benefit_system.reset_parameter_caches.assert_called_once()

    def test__given_modifier__then_clears_computed_variable_caches(self):
        """Given: Modifier function and a simulation with computed variables
        When: Calling the modifier
        Then: Clears holder arrays for variables that have formulas, preserves input variables
        """
        # Given
        mock_holder_computed = MagicMock()
        mock_holder_input = MagicMock()

        mock_variable_computed = MagicMock()
        mock_variable_computed.formulas = {"2000-01-01": lambda: None}

        mock_variable_input = MagicMock()
        mock_variable_input.formulas = {}

        mock_population = MagicMock()
        mock_population._holders = {
            "computed_var": mock_holder_computed,
            "input_var": mock_holder_input,
        }

        mock_simulation = MagicMock()
        mock_param_node = MagicMock()
        mock_simulation.tax_benefit_system.parameters.get_child.return_value = (
            mock_param_node
        )
        mock_simulation.populations = {"person": mock_population}
        mock_simulation.tax_benefit_system.get_variable.side_effect = (
            lambda name: mock_variable_computed
            if name == "computed_var"
            else mock_variable_input
        )

        modifier = simulation_modifier_from_parameter_values([SINGLE_PARAM_VALUE])

        # When
        modifier(mock_simulation)

        # Then
        mock_holder_computed.delete_arrays.assert_called_once()
        mock_holder_input.delete_arrays.assert_not_called()


# Integration tests using the UK tax-benefit model

def test_parameter_reform_affects_calculation():
    """Test that modifying a parameter actually changes the calculation result."""
    from policyengine.core.policy import ParameterValue as PEParameterValue
    from policyengine.core.policy import Policy as PEPolicy
    from policyengine.tax_benefit_models.uk import uk_latest
    from policyengine.tax_benefit_models.uk.analysis import (
        UKHouseholdInput,
        calculate_household_impact,
    )

    param_lookup = {p.name: p for p in uk_latest.parameters}
    pe_param = param_lookup["gov.dwp.universal_credit.standard_allowance.amount.SINGLE_OLD"]

    pe_input = UKHouseholdInput(
        people=[{"age": 30, "employment_income": 0}],
        benunit={},
        household={},
        year=2026,
    )

    # Baseline
    baseline = calculate_household_impact(pe_input, policy=None)
    baseline_uc = baseline.benunit[0]["universal_credit"]

    # Reform - increase standard allowance
    pv = PEParameterValue(
        parameter=pe_param,
        value=533.0,
        start_date=datetime(2026, 1, 1),
        end_date=None,
    )
    policy = PEPolicy(name="Test", description="Test", parameter_values=[pv])
    reform = calculate_household_impact(pe_input, policy=policy)
    reform_uc = reform.benunit[0]["universal_credit"]

    # UC should increase
    assert reform_uc > baseline_uc
    assert abs(reform_uc - 533 * 12) < 1


def test_parameter_reform_preserves_inputs():
    """Test that input variables are preserved when applying a reform."""
    from policyengine.core.policy import ParameterValue as PEParameterValue
    from policyengine.core.policy import Policy as PEPolicy
    from policyengine.tax_benefit_models.uk import uk_latest
    from policyengine.tax_benefit_models.uk.analysis import (
        UKHouseholdInput,
        calculate_household_impact,
    )

    param_lookup = {p.name: p for p in uk_latest.parameters}
    pe_param = param_lookup["gov.dwp.universal_credit.standard_allowance.amount.SINGLE_OLD"]

    pe_input = UKHouseholdInput(
        people=[{"age": 30, "employment_income": 5000}],
        benunit={},
        household={},
        year=2026,
    )

    pv = PEParameterValue(
        parameter=pe_param,
        value=533.0,
        start_date=datetime(2026, 1, 1),
        end_date=None,
    )
    policy = PEPolicy(name="Test", description="Test", parameter_values=[pv])
    reform = calculate_household_impact(pe_input, policy=policy)

    assert reform.person[0]["employment_income"] == 5000
    assert reform.person[0]["age"] == 30
