"""Tests for datasets.py utilities."""

import pytest
from policyengine.utils.data.datasets import (
    process_gs_path,
    determine_us_region_type,
    parse_us_place_region,
    get_us_state_dataset_path,
    _get_default_us_dataset,
    US_DATA_BUCKET,
)


class TestProcessGsPath:
    """Tests for process_gs_path function."""

    def test_basic_path(self):
        """Test parsing a basic gs:// path without version."""
        bucket, path, version = process_gs_path(
            "gs://my-bucket/path/to/file.h5"
        )
        assert bucket == "my-bucket"
        assert path == "path/to/file.h5"
        assert version is None

    def test_path_with_version(self):
        """Test parsing a gs:// path with @version suffix."""
        bucket, path, version = process_gs_path(
            "gs://my-bucket/path/to/file.h5@1.2.3"
        )
        assert bucket == "my-bucket"
        assert path == "path/to/file.h5"
        assert version == "1.2.3"

    def test_path_with_numeric_version(self):
        """Test parsing a gs:// path with numeric version (GCS generation)."""
        bucket, path, version = process_gs_path(
            "gs://my-bucket/file.h5@1234567890"
        )
        assert bucket == "my-bucket"
        assert path == "file.h5"
        assert version == "1234567890"

    def test_path_with_nested_directories(self):
        """Test parsing a gs:// path with deeply nested directories."""
        bucket, path, version = process_gs_path(
            "gs://policyengine-us-data/states/CA/districts/01.h5@2024.1.0"
        )
        assert bucket == "policyengine-us-data"
        assert path == "states/CA/districts/01.h5"
        assert version == "2024.1.0"

    def test_invalid_path_no_gs_prefix(self):
        """Test that non-gs:// paths raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            process_gs_path("https://storage.googleapis.com/bucket/file.h5")
        assert "Invalid gs:// URL format" in str(exc_info.value)

    def test_invalid_path_no_file(self):
        """Test that paths without a file path raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            process_gs_path("gs://bucket-only")
        assert "Invalid gs:// URL format" in str(exc_info.value)

    def test_real_policyengine_paths(self):
        """Test parsing actual PolicyEngine dataset paths."""
        # US data path
        bucket, path, version = process_gs_path(
            "gs://policyengine-us-data/cps_2023.h5"
        )
        assert bucket == "policyengine-us-data"
        assert path == "cps_2023.h5"
        assert version is None

        # UK data path with version
        bucket, path, version = process_gs_path(
            "gs://policyengine-uk-data-private/enhanced_frs_2023_24.h5@1.0.0"
        )
        assert bucket == "policyengine-uk-data-private"
        assert path == "enhanced_frs_2023_24.h5"
        assert version == "1.0.0"

        # State-level dataset
        bucket, path, version = process_gs_path(
            "gs://policyengine-us-data/states/CA.h5"
        )
        assert bucket == "policyengine-us-data"
        assert path == "states/CA.h5"
        assert version is None


class TestDetermineUsRegionType:
    """Tests for determine_us_region_type function with place regions."""

    def test__given__place_region_string__then__returns_place(self):
        # Given
        region = "place/NJ-57000"

        # When
        result = determine_us_region_type(region)

        # Then
        assert result == "place"

    def test__given__place_region_with_different_state__then__returns_place(
        self,
    ):
        # Given
        region = "place/CA-44000"

        # When
        result = determine_us_region_type(region)

        # Then
        assert result == "place"

    def test__given__none_region__then__returns_nationwide(self):
        # Given
        region = None

        # When
        result = determine_us_region_type(region)

        # Then
        assert result == "nationwide"

    def test__given__us_region__then__returns_nationwide(self):
        # Given
        region = "us"

        # When
        result = determine_us_region_type(region)

        # Then
        assert result == "nationwide"

    def test__given__state_region__then__returns_state(self):
        # Given
        region = "state/CA"

        # When
        result = determine_us_region_type(region)

        # Then
        assert result == "state"

    def test__given__congressional_district_region__then__returns_congressional_district(
        self,
    ):
        # Given
        region = "congressional_district/CA-01"

        # When
        result = determine_us_region_type(region)

        # Then
        assert result == "congressional_district"

    def test__given__city_region__then__returns_city(self):
        # Given
        region = "city/nyc"

        # When
        result = determine_us_region_type(region)

        # Then
        assert result == "city"

    def test__given__invalid_region__then__raises_value_error(self):
        # Given
        region = "invalid/something"

        # When / Then
        with pytest.raises(ValueError) as exc_info:
            determine_us_region_type(region)

        assert "Unrecognized US region format" in str(exc_info.value)


class TestParseUsPlaceRegion:
    """Tests for parse_us_place_region function."""

    def test__given__nj_paterson_region__then__returns_nj_and_57000(self):
        # Given
        region = "place/NJ-57000"

        # When
        state_code, place_fips = parse_us_place_region(region)

        # Then
        assert state_code == "NJ"
        assert place_fips == "57000"

    def test__given__ca_los_angeles_region__then__returns_ca_and_44000(self):
        # Given
        region = "place/CA-44000"

        # When
        state_code, place_fips = parse_us_place_region(region)

        # Then
        assert state_code == "CA"
        assert place_fips == "44000"

    def test__given__tx_houston_region__then__returns_tx_and_35000(self):
        # Given
        region = "place/TX-35000"

        # When
        state_code, place_fips = parse_us_place_region(region)

        # Then
        assert state_code == "TX"
        assert place_fips == "35000"

    def test__given__lowercase_state_code__then__returns_lowercase(self):
        # Given
        region = "place/ny-51000"

        # When
        state_code, place_fips = parse_us_place_region(region)

        # Then
        assert state_code == "ny"
        assert place_fips == "51000"

    def test__given__place_fips_with_leading_zeros__then__preserves_zeros(
        self,
    ):
        # Given
        region = "place/AL-07000"

        # When
        state_code, place_fips = parse_us_place_region(region)

        # Then
        assert state_code == "AL"
        assert place_fips == "07000"


class TestGetDefaultUsDatasetForPlace:
    """Tests for _get_default_us_dataset with place regions."""

    def test__given__place_region__then__returns_state_dataset_path(self):
        # Given
        region = "place/NJ-57000"

        # When
        result = _get_default_us_dataset(region)

        # Then
        expected = f"{US_DATA_BUCKET}/states/NJ.h5"
        assert result == expected

    def test__given__ca_place_region__then__returns_ca_state_dataset(self):
        # Given
        region = "place/CA-44000"

        # When
        result = _get_default_us_dataset(region)

        # Then
        expected = f"{US_DATA_BUCKET}/states/CA.h5"
        assert result == expected

    def test__given__lowercase_state_in_place__then__returns_uppercase_state_path(
        self,
    ):
        # Given
        region = "place/tx-35000"

        # When
        result = _get_default_us_dataset(region)

        # Then
        # get_us_state_dataset_path uppercases the state code
        expected = f"{US_DATA_BUCKET}/states/TX.h5"
        assert result == expected

    def test__given__place_region__then__result_matches_state_region_dataset(
        self,
    ):
        # Given
        place_region = "place/GA-04000"
        state_region = "state/GA"

        # When
        place_result = _get_default_us_dataset(place_region)
        state_result = _get_default_us_dataset(state_region)

        # Then
        # Place regions should load the same dataset as their parent state
        assert place_result == state_result
