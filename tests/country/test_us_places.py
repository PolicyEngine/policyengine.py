"""Tests for US place-level (city) filtering functionality."""

import pytest
import pandas as pd
from unittest.mock import Mock, patch

from tests.fixtures.country.us_places import (
    # Place FIPS Constants
    NJ_PATERSON_FIPS,
    NJ_NEWARK_FIPS,
    NJ_JERSEY_CITY_FIPS,
    CA_LOS_ANGELES_FIPS,
    TX_HOUSTON_FIPS,
    NONEXISTENT_PLACE_FIPS,
    # Region String Constants
    NJ_PATERSON_REGION,
    NJ_NEWARK_REGION,
    # Test Data Arrays
    MIXED_PLACES_WITH_PATERSON,
    PLACES_WITHOUT_PATERSON,
    ALL_PATERSON_PLACES,
    MIXED_PLACES_BYTES,
    MULTIPLE_NJ_PLACES,
    TWO_PLACES_FOR_REFORM_TEST,
    # Expected Results Constants
    EXPECTED_PATERSON_COUNT_IN_MIXED,
    EXPECTED_PATERSON_COUNT_IN_BYTES,
    EXPECTED_NEWARK_COUNT_IN_MULTIPLE_NJ,
    MINI_DATASET_PATERSON_COUNT,
    MINI_DATASET_PATERSON_IDS,
    MINI_DATASET_NEWARK_COUNT,
    MINI_DATASET_NEWARK_IDS,
    MINI_DATASET_JERSEY_CITY_COUNT,
    MINI_DATASET_JERSEY_CITY_IDS,
    MINI_DATASET_PATERSON_TOTAL_WEIGHT,
    MINI_DATASET_NEWARK_TOTAL_WEIGHT,
    MINI_DATASET_JERSEY_CITY_TOTAL_WEIGHT,
    MINI_DATASET_BYTES_PATERSON_COUNT,
    MINI_DATASET_BYTES_PATERSON_IDS,
    # Factory Functions
    create_mock_simulation_with_place_fips,
    create_mock_simulation_with_bytes_place_fips,
    create_mock_simulation_type,
    create_simulation_instance,
)


class TestFilterUsSimulationByPlace:
    """Tests for the _filter_us_simulation_by_place method."""

    def test__given__households_in_target_place__then__filters_to_matching_households(
        self,
    ):
        # Given
        mock_sim = create_mock_simulation_with_place_fips(
            MIXED_PLACES_WITH_PATERSON
        )
        mock_simulation_type = create_mock_simulation_type()

        # When
        sim_instance = create_simulation_instance()
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=NJ_PATERSON_REGION,
            reform=None,
        )

        # Then
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        assert len(filtered_df) == EXPECTED_PATERSON_COUNT_IN_MIXED
        assert all(filtered_df["place_fips"] == NJ_PATERSON_FIPS)

    def test__given__no_households_in_target_place__then__returns_empty_dataset(
        self,
    ):
        # Given
        mock_sim = create_mock_simulation_with_place_fips(
            PLACES_WITHOUT_PATERSON
        )
        mock_simulation_type = create_mock_simulation_type()

        # When
        sim_instance = create_simulation_instance()
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=NJ_PATERSON_REGION,
            reform=None,
        )

        # Then
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        assert len(filtered_df) == 0

    def test__given__all_households_in_target_place__then__returns_all_households(
        self,
    ):
        # Given
        mock_sim = create_mock_simulation_with_place_fips(ALL_PATERSON_PLACES)
        mock_simulation_type = create_mock_simulation_type()

        # When
        sim_instance = create_simulation_instance()
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=NJ_PATERSON_REGION,
            reform=None,
        )

        # Then
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        assert len(filtered_df) == len(ALL_PATERSON_PLACES)

    def test__given__bytes_place_fips_in_dataset__then__still_filters_correctly(
        self,
    ):
        # Given: place_fips stored as bytes (as it might be in HDF5)
        mock_sim = create_mock_simulation_with_bytes_place_fips(
            MIXED_PLACES_BYTES
        )
        mock_simulation_type = create_mock_simulation_type()

        # When
        sim_instance = create_simulation_instance()
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=NJ_PATERSON_REGION,
            reform=None,
        )

        # Then
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        assert len(filtered_df) == EXPECTED_PATERSON_COUNT_IN_BYTES

    def test__given__reform_provided__then__passes_reform_to_simulation_type(
        self,
    ):
        # Given
        mock_sim = create_mock_simulation_with_place_fips(
            TWO_PLACES_FOR_REFORM_TEST
        )
        mock_simulation_type = create_mock_simulation_type()
        mock_reform = Mock()

        # When
        sim_instance = create_simulation_instance()
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=NJ_PATERSON_REGION,
            reform=mock_reform,
        )

        # Then
        call_args = mock_simulation_type.call_args
        assert call_args.kwargs["reform"] is mock_reform

    def test__given__different_place_in_same_state__then__filters_correctly(
        self,
    ):
        # Given: Multiple NJ places
        mock_sim = create_mock_simulation_with_place_fips(MULTIPLE_NJ_PLACES)
        mock_simulation_type = create_mock_simulation_type()

        # When: Filter for Newark only
        sim_instance = create_simulation_instance()
        result = sim_instance._filter_us_simulation_by_place(
            simulation=mock_sim,
            simulation_type=mock_simulation_type,
            region=NJ_NEWARK_REGION,
            reform=None,
        )

        # Then
        call_args = mock_simulation_type.call_args
        filtered_df = call_args.kwargs["dataset"]

        assert len(filtered_df) == EXPECTED_NEWARK_COUNT_IN_MULTIPLE_NJ
        assert all(filtered_df["place_fips"] == NJ_NEWARK_FIPS)


class TestApplyUsRegionToSimulationWithPlace:
    """Tests for _apply_us_region_to_simulation with place regions."""

    def test__given__place_region__then__calls_filter_by_place(self):
        # Given
        sim_instance = create_simulation_instance()
        mock_simulation = Mock()
        mock_simulation_type = Mock

        # When / Then
        with patch.object(
            sim_instance,
            "_filter_us_simulation_by_place",
            return_value=Mock(),
        ) as mock_filter:
            result = sim_instance._apply_us_region_to_simulation(
                simulation=mock_simulation,
                simulation_type=mock_simulation_type,
                region=NJ_PATERSON_REGION,
                reform=None,
            )

            mock_filter.assert_called_once_with(
                simulation=mock_simulation,
                simulation_type=mock_simulation_type,
                region=NJ_PATERSON_REGION,
                reform=None,
            )


class TestMiniDatasetPlaceFiltering:
    """Integration-style tests using a mini in-memory dataset.

    Uses the mini_place_dataset fixture from conftest.py.
    """

    def test__given__mini_dataset__then__paterson_filter_returns_correct_count(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset

        # When
        filtered_df = df[df["place_fips"] == NJ_PATERSON_FIPS]

        # Then
        assert len(filtered_df) == MINI_DATASET_PATERSON_COUNT
        assert filtered_df["household_id"].tolist() == MINI_DATASET_PATERSON_IDS

    def test__given__mini_dataset__then__newark_filter_returns_correct_count(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset

        # When
        filtered_df = df[df["place_fips"] == NJ_NEWARK_FIPS]

        # Then
        assert len(filtered_df) == MINI_DATASET_NEWARK_COUNT
        assert filtered_df["household_id"].tolist() == MINI_DATASET_NEWARK_IDS

    def test__given__mini_dataset__then__jersey_city_filter_returns_correct_count(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset

        # When
        filtered_df = df[df["place_fips"] == NJ_JERSEY_CITY_FIPS]

        # Then
        assert len(filtered_df) == MINI_DATASET_JERSEY_CITY_COUNT
        assert (
            filtered_df["household_id"].tolist()
            == MINI_DATASET_JERSEY_CITY_IDS
        )

    def test__given__mini_dataset__then__total_weight_sums_correctly_per_place(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset

        # When
        paterson_weight = df[df["place_fips"] == NJ_PATERSON_FIPS][
            "household_weight"
        ].sum()
        newark_weight = df[df["place_fips"] == NJ_NEWARK_FIPS][
            "household_weight"
        ].sum()
        jersey_city_weight = df[df["place_fips"] == NJ_JERSEY_CITY_FIPS][
            "household_weight"
        ].sum()

        # Then
        assert paterson_weight == MINI_DATASET_PATERSON_TOTAL_WEIGHT
        assert newark_weight == MINI_DATASET_NEWARK_TOTAL_WEIGHT
        assert jersey_city_weight == MINI_DATASET_JERSEY_CITY_TOTAL_WEIGHT

    def test__given__mini_dataset__then__nonexistent_place_returns_empty(
        self, mini_place_dataset
    ):
        # Given
        df = mini_place_dataset

        # When
        filtered_df = df[df["place_fips"] == NONEXISTENT_PLACE_FIPS]

        # Then
        assert len(filtered_df) == 0

    def test__given__mini_dataset_with_bytes_fips__then__filtering_works(
        self, mini_place_dataset_with_bytes
    ):
        # Given
        df = mini_place_dataset_with_bytes

        # When: Filter handling both str and bytes
        mask = (df["place_fips"] == NJ_PATERSON_FIPS) | (
            df["place_fips"] == NJ_PATERSON_FIPS.encode()
        )
        filtered_df = df[mask]

        # Then
        assert len(filtered_df) == MINI_DATASET_BYTES_PATERSON_COUNT
        assert (
            filtered_df["household_id"].tolist()
            == MINI_DATASET_BYTES_PATERSON_IDS
        )
