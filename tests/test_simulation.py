from .fixtures.simulation import (
    uk_sim_options_no_data,
    uk_sim_options_pe_dataset,
    us_sim_options_cps_dataset,
    mock_get_default_dataset,
    mock_dataset,
    SAMPLE_DATASET_FILENAME,
    mock_simulation_with_cliff_vars,
)
import sys
from copy import deepcopy

from policyengine import Simulation
from policyengine.outputs.macro.single.calculate_single_economy import (
    GeneralEconomyTask,
)


class TestSimulation:
    class TestSetData:
        def test__given_no_data_option__sets_default_dataset(
            self, mock_get_default_dataset, mock_dataset
        ):

            # Don't run entire init script
            sim = object.__new__(Simulation)
            sim.options = deepcopy(uk_sim_options_no_data)
            sim._set_data(uk_sim_options_no_data.data)

        def test__given_pe_dataset__sets_data_option_to_dataset(
            self, mock_dataset
        ):

            sim = object.__new__(Simulation)
            sim.options = deepcopy(uk_sim_options_pe_dataset)
            sim._set_data(uk_sim_options_pe_dataset.data)

        def test__given_cps_2023_in_filename__sets_time_period_to_2023(
            self, mock_dataset
        ):
            from policyengine import Simulation

            sim = object.__new__(Simulation)
            sim.options = deepcopy(us_sim_options_cps_dataset)
            sim._set_data(us_sim_options_cps_dataset.data)

    class TestSetDataTimePeriod:
        def test__given_dataset_with_time_period__sets_time_period(self):
            from policyengine import Simulation

            sim = object.__new__(Simulation)

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
            assert (
                sim._set_data_time_period(uk_sim_options_pe_dataset.data)
                == None
            )

    class TestCalculateCliffs:
        def test__calculates_correct_cliff_metrics(
            self, mock_simulation_with_cliff_vars
        ):

            task = object.__new__(GeneralEconomyTask)
            task.simulation = mock_simulation_with_cliff_vars

            cliff_result = task.calculate_cliffs()

            assert cliff_result.cliff_gap == 100.0
            assert cliff_result.cliff_share == 0.5
