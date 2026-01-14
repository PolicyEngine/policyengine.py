"""Tests for US congressional district breakdown functionality."""

import pytest
from tests.fixtures.simulation import create_mock_single_economy
from policyengine.outputs.macro.comparison.calculate_economy_comparison import (
    us_congressional_district_breakdown,
    USCongressionalDistrictBreakdownWithValues,
    USCongressionalDistrictImpact,
)
from policyengine.utils.geography import geoid_to_district_name


class TestGeoidToDistrictName:
    """Tests for the geoid_to_district_name helper function."""

    def test__given_georgia_district_5_geoid__then_returns_ga_05(self):
        # Given
        geoid = 1305  # State FIPS 13 (GA) + District 05

        # When
        result = geoid_to_district_name(geoid)

        # Then
        assert result == "GA-05"

    def test__given_california_district_12_geoid__then_returns_ca_12(self):
        # Given
        geoid = 612  # State FIPS 6 (CA) + District 12

        # When
        result = geoid_to_district_name(geoid)

        # Then
        assert result == "CA-12"

    def test__given_north_carolina_district_4_geoid__then_returns_nc_04(self):
        # Given
        geoid = 3704  # State FIPS 37 (NC) + District 04

        # When
        result = geoid_to_district_name(geoid)

        # Then
        assert result == "NC-04"

    def test__given_single_digit_district__then_pads_with_zero(self):
        # Given
        geoid = 101  # State FIPS 1 (AL) + District 01

        # When
        result = geoid_to_district_name(geoid)

        # Then
        assert result == "AL-01"


class TestUsCongressionalDistrictBreakdown:
    """Tests for the us_congressional_district_breakdown function."""

    def test__given_non_us_country__then_returns_none(
        self, mock_single_economy_with_ga_districts
    ):
        # Given
        baseline = mock_single_economy_with_ga_districts
        reform = mock_single_economy_with_ga_districts
        country_id = "uk"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        assert result is None

    def test__given_null_district_geoids__then_returns_none(
        self, mock_single_economy_with_null_districts
    ):
        # Given
        baseline = mock_single_economy_with_null_districts
        reform = mock_single_economy_with_null_districts
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        assert result is None

    def test__given_all_zero_district_geoids__then_returns_none(
        self, mock_single_economy_without_districts
    ):
        # Given
        baseline = mock_single_economy_without_districts
        reform = mock_single_economy_without_districts
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        assert result is None

    def test__given_valid_district_data__then_returns_breakdown_with_districts_list(
        self, mock_single_economy_with_ga_districts
    ):
        # Given
        baseline = mock_single_economy_with_ga_districts
        reform = mock_single_economy_with_ga_districts
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        assert result is not None
        assert isinstance(result, USCongressionalDistrictBreakdownWithValues)
        assert hasattr(result, "districts")
        assert isinstance(result.districts, list)

    def test__given_two_ga_districts__then_returns_two_district_impacts(
        self, mock_single_economy_with_ga_districts
    ):
        # Given
        baseline = mock_single_economy_with_ga_districts
        reform = mock_single_economy_with_ga_districts
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        assert len(result.districts) == 2
        district_names = [d.district for d in result.districts]
        assert "GA-05" in district_names
        assert "GA-06" in district_names

    def test__given_districts_from_multiple_states__then_returns_all_districts_sorted(
        self, mock_single_economy_with_multi_state_districts
    ):
        # Given
        baseline = mock_single_economy_with_multi_state_districts
        reform = mock_single_economy_with_multi_state_districts
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        assert len(result.districts) == 4
        district_names = [d.district for d in result.districts]
        # Should be sorted alphabetically
        assert district_names == ["GA-05", "GA-06", "NC-04", "NC-12"]

    def test__given_no_income_change__then_returns_zero_changes(
        self, mock_single_economy_with_ga_districts
    ):
        # Given: baseline and reform are identical
        baseline = mock_single_economy_with_ga_districts
        reform = mock_single_economy_with_ga_districts
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        for district in result.districts:
            assert district.average_household_income_change == 0.0
            assert district.relative_household_income_change == 0.0

    def test__given_income_increase__then_returns_positive_changes(self):
        # Given: reform has higher incomes than baseline
        baseline = create_mock_single_economy(
            household_net_income=[50000.0, 60000.0, 70000.0],
            household_weight=[1000.0, 1000.0, 1000.0],
            congressional_district_geoid=[1305, 1305, 1305],
        )
        reform = create_mock_single_economy(
            household_net_income=[51000.0, 61000.0, 71000.0],
            household_weight=[1000.0, 1000.0, 1000.0],
            congressional_district_geoid=[1305, 1305, 1305],
        )
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        assert len(result.districts) == 1
        district = result.districts[0]
        assert district.district == "GA-05"
        assert district.average_household_income_change == 1000.0
        assert district.relative_household_income_change > 0

    def test__given_income_decrease__then_returns_negative_changes(self):
        # Given: reform has lower incomes than baseline
        baseline = create_mock_single_economy(
            household_net_income=[50000.0, 60000.0, 70000.0],
            household_weight=[1000.0, 1000.0, 1000.0],
            congressional_district_geoid=[1305, 1305, 1305],
        )
        reform = create_mock_single_economy(
            household_net_income=[49000.0, 59000.0, 69000.0],
            household_weight=[1000.0, 1000.0, 1000.0],
            congressional_district_geoid=[1305, 1305, 1305],
        )
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        assert len(result.districts) == 1
        district = result.districts[0]
        assert district.district == "GA-05"
        assert district.average_household_income_change == -1000.0
        assert district.relative_household_income_change < 0

    def test__given_weighted_households__then_calculates_weighted_averages(
        self,
    ):
        # Given: households with different weights
        baseline = create_mock_single_economy(
            household_net_income=[50000.0, 100000.0],
            household_weight=[3000.0, 1000.0],  # First household has 3x weight
            congressional_district_geoid=[1305, 1305],
        )
        reform = create_mock_single_economy(
            household_net_income=[51000.0, 101000.0],
            household_weight=[3000.0, 1000.0],
            congressional_district_geoid=[1305, 1305],
        )
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        district = result.districts[0]
        # Weighted sum of income change: (3000*1000 + 1000*1000) = 4,000,000
        # Total households: 3000 + 1000 = 4000
        # Average change: 4,000,000 / 4000 = 1000
        assert district.average_household_income_change == 1000.0

    def test__given_district_impact__then_has_required_fields(
        self, mock_single_economy_with_ga_districts
    ):
        # Given
        baseline = mock_single_economy_with_ga_districts
        reform = mock_single_economy_with_ga_districts
        country_id = "us"

        # When
        result = us_congressional_district_breakdown(
            baseline, reform, country_id
        )

        # Then
        for district in result.districts:
            assert isinstance(district, USCongressionalDistrictImpact)
            assert hasattr(district, "district")
            assert hasattr(district, "average_household_income_change")
            assert hasattr(district, "relative_household_income_change")
            assert isinstance(district.district, str)
            assert isinstance(district.average_household_income_change, float)
            assert isinstance(district.relative_household_income_change, float)


class TestCongressionalDistrictGeoidExtraction:
    """Tests for congressional_district_geoid extraction in SingleEconomy."""

    def test__given_us_simulation_with_state_dataset__then_geoid_is_extracted(
        self,
    ):
        """Integration test: verify geoid extraction works with real simulation.

        Note: This test requires network access to download state dataset.
        Skip if running in isolated environment.
        """
        pytest.importorskip("policyengine_us")

        from policyengine import Simulation

        # Given: A US state simulation (GA has district assignments)
        sim = Simulation(
            scope="macro",
            country="us",
            region="state/GA",
            time_period=2025,
        )

        # When
        result = sim.calculate_single_economy()

        # Then
        assert result.congressional_district_geoid is not None
        assert len(result.congressional_district_geoid) > 0
        # All geoids should be in Georgia (FIPS 13xx)
        non_zero_geoids = [
            g for g in result.congressional_district_geoid if g > 0
        ]
        assert len(non_zero_geoids) > 0
        for geoid in non_zero_geoids:
            state_fips = geoid // 100
            assert (
                state_fips == 13
            ), f"Expected GA (13), got state FIPS {state_fips}"
