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

from tests.fixtures.country.us_places import (
    mock_simulation_type,
    mock_reform,
    simulation_instance,
    mock_sim_mixed_places,
    mock_sim_no_paterson,
    mock_sim_all_paterson,
    mock_sim_bytes_places,
    mock_sim_multiple_nj_places,
    mock_sim_for_reform_test,
    mini_place_dataset,
    mini_place_dataset_with_bytes,
)
