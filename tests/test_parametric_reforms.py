"""Tests for parametric reforms utility functions."""

from datetime import date

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
        assert "2024-01-01.2100-12-31" in result[MOCK_PARAM_SINGLE.name]
        assert result[MOCK_PARAM_SINGLE.name]["2024-01-01.2100-12-31"] == 29200

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
        """Given: Multiple open-ended values for same parameter (different periods)
        When: Calling reform_dict_from_parameter_values
        Then: Each value runs until the next-later value starts
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
        assert result[param_name]["2024-01-01.2024-12-31"] == 29200
        assert result[param_name]["2025-01-01.2100-12-31"] == 30000

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
        assert result[MOCK_PARAM_SINGLE.name]["2024-01-01.2100-12-31"] == 29200
        assert result[MOCK_PARAM_JOINT.name]["2024-01-01.2100-12-31"] == 58400
        assert result[MOCK_PARAM_TAX_RATE.name]["2024-01-01.2100-12-31"] == 0.10

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
        assert result["gov.test.rate"]["2024-01-01.2100-12-31"] == 0.15
        assert isinstance(result["gov.test.rate"]["2024-01-01.2100-12-31"], float)

    def test__given_open_ended_value__then_period_stops_far_future(self):
        """Given: Parameter value with no end date (open-ended)
        When: Calling reform_dict_from_parameter_values
        Then: Emits an explicit far-future stop instead of a bare start
        date, which policyengine-core Reform.from_dict would apply for a
        single instant only (issue #453)
        """
        # Given
        pv = SINGLE_PARAM_VALUE

        # When
        result = reform_dict_from_parameter_values([pv])

        # Then
        (period_key,) = result[MOCK_PARAM_SINGLE.name]
        assert period_key == "2024-01-01.2100-12-31"

    def test__given_open_ended_values_in_reverse_order__then_clips_at_next_start(
        self,
    ):
        """Given: Two open-ended values for one parameter, listed latest-first
        When: Calling reform_dict_from_parameter_values
        Then: The earlier value stops the day before the later one starts,
        regardless of list order
        """
        # Given
        param = create_mock_parameter("gov.test.step")
        later = create_parameter_value(
            parameter=param, value=2_000, start_date=date(2028, 1, 1)
        )
        earlier = create_parameter_value(
            parameter=param, value=1_000, start_date=date(2026, 1, 1)
        )

        # When
        result = reform_dict_from_parameter_values([later, earlier])

        # Then
        assert result["gov.test.step"] == {
            "2028-01-01.2100-12-31": 2_000,
            "2026-01-01.2027-12-31": 1_000,
        }

    def test__given_open_ended_and_explicit_end_values__then_open_ended_clips_at_next_start(
        self,
    ):
        """Given: An open-ended value followed by a later value with an explicit end
        When: Calling reform_dict_from_parameter_values
        Then: The open-ended value stops the day before the later value
        starts; the explicit end is preserved verbatim
        """
        # Given
        param = create_mock_parameter("gov.test.mixed")
        open_ended = create_parameter_value(
            parameter=param, value=100, start_date=date(2024, 1, 1)
        )
        bounded = create_parameter_value(
            parameter=param,
            value=200,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        # When
        result = reform_dict_from_parameter_values([open_ended, bounded])

        # Then
        assert result["gov.test.mixed"] == {
            "2024-01-01.2025-12-31": 100,
            "2026-01-01.2026-12-31": 200,
        }


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
        from unittest.mock import MagicMock

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
        from unittest.mock import MagicMock

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
        assert mock_simulation.tax_benefit_system.parameters.get_child.call_count == 3
        assert mock_param_node.update.call_count == 3

    def test__given_modifier__then_returns_simulation(self):
        """Given: Modifier function
        When: Calling with a simulation
        Then: Returns the simulation object
        """
        # Given
        from unittest.mock import MagicMock

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
