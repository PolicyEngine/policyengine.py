"""Tests for datasets.py utilities."""

import pytest
from policyengine.utils.data.datasets import process_gs_path


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
