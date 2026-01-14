"""Pytest configuration and shared fixtures."""

import pytest

# Re-export fixtures from fixtures module
from tests.fixtures.simulation import (
    mock_get_default_dataset,
    mock_dataset,
    mock_simulation_with_cliff_vars,
    mock_single_economy_with_ga_districts,
    mock_single_economy_with_multi_state_districts,
    mock_single_economy_without_districts,
    mock_single_economy_with_null_districts,
)
