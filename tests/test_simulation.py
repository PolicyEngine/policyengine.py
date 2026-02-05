from .fixtures.simulation import (
    get_uk_sim_options_no_data,
    get_uk_sim_options_pe_dataset,
    get_us_sim_options_cps_dataset,
    mock_get_default_dataset,
    mock_dataset,
    SAMPLE_DATASET_FILENAME,
    mock_simulation_with_cliff_vars,
)
import sys
import pytest
from copy import deepcopy
from unittest.mock import Mock


class TestSimulation:
    class TestSetData:
        def test__given_no_data_option__sets_default_dataset(
            self, mock_get_default_dataset, mock_dataset
        ):
            from policyengine import Simulation

            # Don't run entire init script
            sim = object.__new__(Simulation)
            uk_sim_options_no_data = get_uk_sim_options_no_data()
            sim.options = deepcopy(uk_sim_options_no_data)
            sim._set_data(uk_sim_options_no_data.data)

        def test__given_pe_dataset__sets_data_option_to_dataset(
            self, mock_dataset
        ):
            from policyengine import Simulation

            sim = object.__new__(Simulation)
            uk_sim_options_pe_dataset = get_uk_sim_options_pe_dataset()
            sim.options = deepcopy(uk_sim_options_pe_dataset)
            sim._set_data(uk_sim_options_pe_dataset.data)

        def test__given_cps_2023_in_filename__sets_time_period_to_2023(
            self, mock_dataset
        ):
            from policyengine import Simulation

            sim = object.__new__(Simulation)
            us_sim_options_cps_dataset = get_us_sim_options_cps_dataset()
            sim.options = deepcopy(us_sim_options_cps_dataset)
            sim._set_data(us_sim_options_cps_dataset.data)

    class TestSetDataTimePeriod:
        def test__given_dataset_with_time_period__sets_time_period(self):
            from policyengine import Simulation

            sim = object.__new__(Simulation)
            us_sim_options_cps_dataset = get_us_sim_options_cps_dataset()
            print("Dataset:", us_sim_options_cps_dataset.data, file=sys.stderr)
            assert (
                sim._set_data_time_period(us_sim_options_cps_dataset.data)
                == 2023
            )

        def test__given_dataset_without_time_period__does_not_set_time_period(
            self,
        ):
            from policyengine import Simulation

            sim = object.__new__(Simulation)
            uk_sim_options_pe_dataset = get_uk_sim_options_pe_dataset()
            assert (
                sim._set_data_time_period(uk_sim_options_pe_dataset.data)
                == None
            )

    class TestCalculateCliffs:
        def test__calculates_correct_cliff_metrics(
            self, mock_simulation_with_cliff_vars
        ):
            from policyengine.outputs.macro.single.calculate_single_economy import (
                GeneralEconomyTask,
            )

            task = object.__new__(GeneralEconomyTask)
            task.simulation = mock_simulation_with_cliff_vars

            cliff_result = task.calculate_cliffs()

            assert cliff_result.cliff_gap == 100.0
            assert cliff_result.cliff_share == 0.5


class TestVariableValidation:
    """Tests for variable validation functions."""

    @staticmethod
    def _create_mock_tbs(variables: dict[str, str]) -> Mock:
        """Create a mock tax-benefit system with specified variables.

        Args:
            variables: Dict mapping variable names to entity keys.

        Returns:
            Mock TBS with variables configured.
        """
        mock_tbs = Mock()
        mock_tbs.variables = {}
        for var_name, entity_key in variables.items():
            mock_var = Mock()
            mock_var.entity = Mock()
            mock_var.entity.key = entity_key
            mock_tbs.variables[var_name] = mock_var
        return mock_tbs

    class TestGetVariable:
        def test__given__existing_variable__then__returns_variable(self):
            from policyengine.simulation import get_variable

            mock_tbs = TestVariableValidation._create_mock_tbs(
                {"place_fips": "household"}
            )

            result = get_variable(mock_tbs, "place_fips")

            assert result is mock_tbs.variables["place_fips"]

        def test__given__nonexistent_variable__then__raises_value_error(self):
            from policyengine.simulation import get_variable

            mock_tbs = TestVariableValidation._create_mock_tbs({})

            with pytest.raises(ValueError) as exc_info:
                get_variable(mock_tbs, "nonexistent")

            assert "not found" in str(exc_info.value)
            assert "nonexistent" in str(exc_info.value)

    class TestValidateVariableEntity:
        def test__given__matching_entity__then__passes(self):
            from policyengine.simulation import validate_variable_entity

            mock_tbs = TestVariableValidation._create_mock_tbs(
                {"place_fips": "household"}
            )

            # Should not raise
            validate_variable_entity(mock_tbs, "place_fips", "household")

        def test__given__mismatched_entity__then__raises_value_error(self):
            from policyengine.simulation import validate_variable_entity

            mock_tbs = TestVariableValidation._create_mock_tbs(
                {"age": "person"}
            )

            with pytest.raises(ValueError) as exc_info:
                validate_variable_entity(mock_tbs, "age", "household")

            assert "person-level" in str(exc_info.value)
            assert "household-level" in str(exc_info.value)

        def test__given__nonexistent_variable__then__raises_value_error(self):
            from policyengine.simulation import validate_variable_entity

            mock_tbs = TestVariableValidation._create_mock_tbs({})

            with pytest.raises(ValueError) as exc_info:
                validate_variable_entity(mock_tbs, "nonexistent", "household")

            assert "not found" in str(exc_info.value)

    class TestValidateHouseholdVariable:
        def test__given__household_variable__then__passes(self):
            from policyengine.simulation import validate_household_variable

            mock_tbs = TestVariableValidation._create_mock_tbs(
                {"place_fips": "household"}
            )

            # Should not raise
            validate_household_variable(mock_tbs, "place_fips")

        def test__given__person_variable__then__raises_value_error(self):
            from policyengine.simulation import validate_household_variable

            mock_tbs = TestVariableValidation._create_mock_tbs(
                {"age": "person"}
            )

            with pytest.raises(ValueError) as exc_info:
                validate_household_variable(mock_tbs, "age")

            assert "person-level" in str(exc_info.value)
            assert "household-level" in str(exc_info.value)

        def test__given__tax_unit_variable__then__raises_value_error(self):
            from policyengine.simulation import validate_household_variable

            mock_tbs = TestVariableValidation._create_mock_tbs(
                {"filing_status": "tax_unit"}
            )

            with pytest.raises(ValueError) as exc_info:
                validate_household_variable(mock_tbs, "filing_status")

            assert "tax_unit-level" in str(exc_info.value)
