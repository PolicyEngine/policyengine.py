"""Tests for US place-level (city) filtering functionality."""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock


class TestFilterUsSimulationByPlace:
    """Tests for the _filter_us_simulation_by_place method."""

    def _create_mock_simulation_with_place_fips(
        self,
        place_fips_values: list[str],
        household_ids: list[int] | None = None,
    ) -> Mock:
        """Create a mock simulation with place_fips data.

        Args:
            place_fips_values: List of place FIPS codes for each household.
            household_ids: Optional list of household IDs.

        Returns:
            Mock simulation object.
        """
        if household_ids is None:
            household_ids = list(range(len(place_fips_values)))

        mock_sim = Mock()

        # Mock calculate to return place_fips values
        mock_calculate_result = Mock()
        mock_calculate_result.values = np.array(place_fips_values)
        mock_sim.calculate.return_value = mock_calculate_result

        # Mock to_input_dataframe to return a DataFrame
        df = pd.DataFrame(
            {
                "household_id": household_ids,
                "place_fips": place_fips_values,
            }
        )
        mock_sim.to_input_dataframe.return_value = df

        return mock_sim

    def test__given__households_in_target_place__then__filters_to_matching_households(
        self,
    ):
        # Given
        place_fips_values = ["57000", "57000", "44000", "35000", "57000"]
        mock_sim = self._create_mock_simulation_with_place_fips(
            place_fips_values
        )

        mock_simulation_type = Mock()
        mock_simulation_type.return_value = Mock()

        region = "place/NJ-57000"
        reform = None

        # When
        from policyengine.simulation import Simulation

        sim_instance = object.__new__(Simulation)
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=region,
            reform=reform,
        )

        # Then
        # Check that simulation_type was called with filtered data
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        # Should have 3 households with place_fips "57000"
        assert len(filtered_df) == 3
        assert all(filtered_df["place_fips"] == "57000")

    def test__given__no_households_in_target_place__then__returns_empty_dataset(
        self,
    ):
        # Given
        place_fips_values = ["44000", "35000", "51000"]
        mock_sim = self._create_mock_simulation_with_place_fips(
            place_fips_values
        )

        mock_simulation_type = Mock()
        mock_simulation_type.return_value = Mock()

        region = "place/NJ-57000"  # No households have this place
        reform = None

        # When
        from policyengine.simulation import Simulation

        sim_instance = object.__new__(Simulation)
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=region,
            reform=reform,
        )

        # Then
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        assert len(filtered_df) == 0

    def test__given__all_households_in_target_place__then__returns_all_households(
        self,
    ):
        # Given
        place_fips_values = ["57000", "57000", "57000"]
        mock_sim = self._create_mock_simulation_with_place_fips(
            place_fips_values
        )

        mock_simulation_type = Mock()
        mock_simulation_type.return_value = Mock()

        region = "place/NJ-57000"
        reform = None

        # When
        from policyengine.simulation import Simulation

        sim_instance = object.__new__(Simulation)
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=region,
            reform=reform,
        )

        # Then
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        assert len(filtered_df) == 3

    def test__given__bytes_place_fips_in_dataset__then__still_filters_correctly(
        self,
    ):
        # Given: place_fips stored as bytes (as it might be in HDF5)
        place_fips_values = [b"57000", b"57000", b"44000", b"35000"]
        mock_sim = Mock()

        mock_calculate_result = Mock()
        mock_calculate_result.values = np.array(place_fips_values)
        mock_sim.calculate.return_value = mock_calculate_result

        df = pd.DataFrame(
            {
                "household_id": [0, 1, 2, 3],
                "place_fips": place_fips_values,
            }
        )
        mock_sim.to_input_dataframe.return_value = df

        mock_simulation_type = Mock()
        mock_simulation_type.return_value = Mock()

        region = "place/NJ-57000"
        reform = None

        # When
        from policyengine.simulation import Simulation

        sim_instance = object.__new__(Simulation)
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=region,
            reform=reform,
        )

        # Then
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        # Should match 2 households with bytes b"57000"
        assert len(filtered_df) == 2

    def test__given__reform_provided__then__passes_reform_to_simulation_type(
        self,
    ):
        # Given
        place_fips_values = ["57000", "44000"]
        mock_sim = self._create_mock_simulation_with_place_fips(
            place_fips_values
        )

        mock_simulation_type = Mock()
        mock_simulation_type.return_value = Mock()

        region = "place/NJ-57000"
        mock_reform = Mock()

        # When
        from policyengine.simulation import Simulation

        sim_instance = object.__new__(Simulation)
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=region,
            reform=mock_reform,
        )

        # Then
        call_args = mock_simulation_type.call_args
        assert call_args.kwargs["reform"] is mock_reform

    def test__given__different_place_in_same_state__then__filters_correctly(
        self,
    ):
        # Given: Multiple NJ places
        place_fips_values = [
            "57000",  # Paterson
            "51000",  # Newark
            "36000",  # Jersey City
            "57000",  # Paterson
            "51000",  # Newark
        ]
        mock_sim = self._create_mock_simulation_with_place_fips(
            place_fips_values
        )

        mock_simulation_type = Mock()
        mock_simulation_type.return_value = Mock()

        # Filter for Newark only
        region = "place/NJ-51000"
        reform = None

        # When
        from policyengine.simulation import Simulation

        sim_instance = object.__new__(Simulation)
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=region,
            reform=reform,
        )

        # Then
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        # Should have 2 Newark households
        assert len(filtered_df) == 2
        assert all(filtered_df["place_fips"] == "51000")


class TestApplyUsRegionToSimulationWithPlace:
    """Tests for _apply_us_region_to_simulation with place regions."""

    def test__given__place_region__then__calls_filter_by_place(self):
        # Given
        from policyengine.simulation import Simulation

        sim_instance = object.__new__(Simulation)

        mock_simulation = Mock()
        mock_simulation_type = Mock

        region = "place/NJ-57000"
        reform = None

        # Mock _filter_us_simulation_by_place
        with patch.object(
            sim_instance,
            "_filter_us_simulation_by_place",
            return_value=Mock(),
        ) as mock_filter:
            # When
            result = sim_instance._apply_us_region_to_simulation(
                simulation=mock_simulation,
                simulation_type=mock_simulation_type,
                region=region,
                reform=reform,
            )

            # Then
            mock_filter.assert_called_once_with(
                simulation=mock_simulation,
                simulation_type=mock_simulation_type,
                region=region,
                reform=reform,
            )


class TestMiniDatasetPlaceFiltering:
    """Integration-style tests using a mini in-memory dataset."""

    @pytest.fixture
    def mini_place_dataset(self) -> pd.DataFrame:
        """Create a mini dataset with place_fips for testing.

        Simulates 10 households across 3 NJ places:
        - Paterson (57000): 4 households
        - Newark (51000): 3 households
        - Jersey City (36000): 3 households
        """
        return pd.DataFrame(
            {
                "household_id": list(range(10)),
                "place_fips": [
                    "57000",
                    "57000",
                    "51000",
                    "36000",
                    "57000",
                    "51000",
                    "36000",
                    "57000",
                    "51000",
                    "36000",
                ],
                "household_weight": [
                    1000.0,
                    1500.0,
                    2000.0,
                    1200.0,
                    800.0,
                    1800.0,
                    1100.0,
                    900.0,
                    1400.0,
                    1300.0,
                ],
                "household_net_income": [
                    50000.0,
                    60000.0,
                    75000.0,
                    45000.0,
                    55000.0,
                    80000.0,
                    40000.0,
                    65000.0,
                    70000.0,
                    48000.0,
                ],
            }
        )

    def test__given__mini_dataset__then__paterson_filter_returns_4_households(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset
        target_place_fips = "57000"  # Paterson

        # When
        filtered_df = df[df["place_fips"] == target_place_fips]

        # Then
        assert len(filtered_df) == 4
        assert filtered_df["household_id"].tolist() == [0, 1, 4, 7]

    def test__given__mini_dataset__then__newark_filter_returns_3_households(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset
        target_place_fips = "51000"  # Newark

        # When
        filtered_df = df[df["place_fips"] == target_place_fips]

        # Then
        assert len(filtered_df) == 3
        assert filtered_df["household_id"].tolist() == [2, 5, 8]

    def test__given__mini_dataset__then__jersey_city_filter_returns_3_households(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset
        target_place_fips = "36000"  # Jersey City

        # When
        filtered_df = df[df["place_fips"] == target_place_fips]

        # Then
        assert len(filtered_df) == 3
        assert filtered_df["household_id"].tolist() == [3, 6, 9]

    def test__given__mini_dataset__then__total_weight_sums_correctly_per_place(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset

        # When
        paterson_weight = df[df["place_fips"] == "57000"][
            "household_weight"
        ].sum()
        newark_weight = df[df["place_fips"] == "51000"][
            "household_weight"
        ].sum()
        jersey_city_weight = df[df["place_fips"] == "36000"][
            "household_weight"
        ].sum()

        # Then
        # Paterson: 1000 + 1500 + 800 + 900 = 4200
        assert paterson_weight == 4200.0
        # Newark: 2000 + 1800 + 1400 = 5200
        assert newark_weight == 5200.0
        # Jersey City: 1200 + 1100 + 1300 = 3600
        assert jersey_city_weight == 3600.0

    def test__given__mini_dataset__then__nonexistent_place_returns_empty(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset
        target_place_fips = "99999"  # Non-existent place

        # When
        filtered_df = df[df["place_fips"] == target_place_fips]

        # Then
        assert len(filtered_df) == 0

    def test__given__mini_dataset_with_bytes_fips__then__filtering_works(self):
        # Given: Dataset with bytes place_fips (as might come from HDF5)
        df = pd.DataFrame(
            {
                "household_id": [0, 1, 2, 3],
                "place_fips": [b"57000", b"57000", b"51000", b"51000"],
                "household_weight": [1000.0, 1000.0, 1000.0, 1000.0],
            }
        )
        target_place_fips = "57000"

        # When: Filter handling both str and bytes
        mask = (df["place_fips"] == target_place_fips) | (
            df["place_fips"] == target_place_fips.encode()
        )
        filtered_df = df[mask]

        # Then
        assert len(filtered_df) == 2
        assert filtered_df["household_id"].tolist() == [0, 1]
