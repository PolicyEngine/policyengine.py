"""Test fixtures for US place-level filtering tests.

These fixtures support testing the entity_rel filtering approach which:
1. Builds explicit entity relationships (person -> household, tax_unit, etc.)
2. Filters at household level to preserve entity integrity
3. Creates new simulations from filtered DataFrames
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock

# =============================================================================
# Place FIPS Constants
# =============================================================================

# New Jersey places
NJ_PATERSON_FIPS = "57000"
NJ_NEWARK_FIPS = "51000"
NJ_JERSEY_CITY_FIPS = "36000"

# Other state places
CA_LOS_ANGELES_FIPS = "44000"
TX_HOUSTON_FIPS = "35000"

# Non-existent place for testing empty results
NONEXISTENT_PLACE_FIPS = "99999"

# Bytes versions (as stored in HDF5)
NJ_PATERSON_FIPS_BYTES = b"57000"
NJ_NEWARK_FIPS_BYTES = b"51000"
CA_LOS_ANGELES_FIPS_BYTES = b"44000"
TX_HOUSTON_FIPS_BYTES = b"35000"

# =============================================================================
# Region String Constants
# =============================================================================

NJ_PATERSON_REGION = "place/NJ-57000"
NJ_NEWARK_REGION = "place/NJ-51000"
NJ_JERSEY_CITY_REGION = "place/NJ-36000"
CA_LOS_ANGELES_REGION = "place/CA-44000"
TX_HOUSTON_REGION = "place/TX-35000"

# =============================================================================
# Test Data Arrays - Place FIPS combinations for various test scenarios
# =============================================================================

# Mixed places: 3 Paterson, 1 LA, 1 Houston (5 total)
MIXED_PLACES_WITH_PATERSON = [
    NJ_PATERSON_FIPS,
    NJ_PATERSON_FIPS,
    CA_LOS_ANGELES_FIPS,
    TX_HOUSTON_FIPS,
    NJ_PATERSON_FIPS,
]

# No Paterson: LA, Houston, Newark (3 total)
PLACES_WITHOUT_PATERSON = [
    CA_LOS_ANGELES_FIPS,
    TX_HOUSTON_FIPS,
    NJ_NEWARK_FIPS,
]

# All Paterson (3 total)
ALL_PATERSON_PLACES = [
    NJ_PATERSON_FIPS,
    NJ_PATERSON_FIPS,
    NJ_PATERSON_FIPS,
]

# Bytes version: 2 Paterson, 1 LA, 1 Houston (4 total)
MIXED_PLACES_BYTES = [
    NJ_PATERSON_FIPS_BYTES,
    NJ_PATERSON_FIPS_BYTES,
    CA_LOS_ANGELES_FIPS_BYTES,
    TX_HOUSTON_FIPS_BYTES,
]

# Multiple NJ places: 2 Paterson, 2 Newark, 1 Jersey City (5 total)
MULTIPLE_NJ_PLACES = [
    NJ_PATERSON_FIPS,
    NJ_NEWARK_FIPS,
    NJ_JERSEY_CITY_FIPS,
    NJ_PATERSON_FIPS,
    NJ_NEWARK_FIPS,
]

# Simple two-place array for reform test
TWO_PLACES_FOR_REFORM_TEST = [
    NJ_PATERSON_FIPS,
    CA_LOS_ANGELES_FIPS,
]

# =============================================================================
# Expected Results Constants
# =============================================================================

# Expected counts when filtering MIXED_PLACES_WITH_PATERSON for Paterson
EXPECTED_PATERSON_COUNT_IN_MIXED = 3

# Expected counts when filtering MIXED_PLACES_BYTES for Paterson
EXPECTED_PATERSON_COUNT_IN_BYTES = 2

# Expected counts when filtering MULTIPLE_NJ_PLACES for Newark
EXPECTED_NEWARK_COUNT_IN_MULTIPLE_NJ = 2

# Mini dataset expected values
MINI_DATASET_PATERSON_COUNT = 4
MINI_DATASET_PATERSON_IDS = [0, 1, 4, 7]
MINI_DATASET_NEWARK_COUNT = 3
MINI_DATASET_NEWARK_IDS = [2, 5, 8]
MINI_DATASET_JERSEY_CITY_COUNT = 3
MINI_DATASET_JERSEY_CITY_IDS = [3, 6, 9]

# Mini dataset expected weights per place
MINI_DATASET_PATERSON_TOTAL_WEIGHT = 4200.0
MINI_DATASET_NEWARK_TOTAL_WEIGHT = 5200.0
MINI_DATASET_JERSEY_CITY_TOTAL_WEIGHT = 3600.0

# Mini dataset with bytes expected values
MINI_DATASET_BYTES_PATERSON_COUNT = 2
MINI_DATASET_BYTES_PATERSON_IDS = [0, 1]


# =============================================================================
# Mock Factory Functions
# =============================================================================


def create_mock_tax_benefit_system(household_variables: list[str] | None = None) -> Mock:
    """Create a mock tax benefit system with variable entity information.

    Args:
        household_variables: List of variable names that are household-level.
            Defaults to ["place_fips"].

    Returns:
        Mock TaxBenefitSystem with variables dict containing entity info.
    """
    if household_variables is None:
        household_variables = ["place_fips"]

    mock_tbs = Mock()
    mock_tbs.variables = {}

    for var_name in household_variables:
        mock_var = Mock()
        mock_var.entity = Mock()
        mock_var.entity.key = "household"
        mock_tbs.variables[var_name] = mock_var

    # Add standard entity ID variables
    for entity_id in ["person_id", "household_id", "tax_unit_id", "spm_unit_id", "family_id", "marital_unit_id"]:
        mock_var = Mock()
        mock_var.entity = Mock()
        # Entity IDs belong to their respective entities
        entity_name = entity_id.replace("_id", "")
        mock_var.entity.key = entity_name if entity_name != "person" else "person"
        mock_tbs.variables[entity_id] = mock_var

    return mock_tbs


def create_mock_simulation_with_place_fips(
    place_fips_values: list[str],
    household_ids: list[int] | None = None,
    persons_per_household: int = 1,
) -> Mock:
    """Create a mock simulation with place_fips data for entity_rel filtering.

    Supports the entity_rel approach by mocking:
    - calculate() with variable-specific return values
    - tax_benefit_system.variables for entity validation
    - to_input_dataframe() returning person-level DataFrame

    Args:
        place_fips_values: List of place FIPS codes for each household.
        household_ids: Optional list of household IDs.
        persons_per_household: Number of persons per household (default 1).

    Returns:
        Mock simulation object configured for entity_rel filtering.
    """
    if household_ids is None:
        household_ids = list(range(len(place_fips_values)))

    num_households = len(place_fips_values)
    num_persons = num_households * persons_per_household

    # Create person-level data by repeating household data
    person_ids = list(range(num_persons))
    person_household_ids = []
    person_place_fips = []
    for i, (hh_id, place) in enumerate(zip(household_ids, place_fips_values)):
        for _ in range(persons_per_household):
            person_household_ids.append(hh_id)
            person_place_fips.append(place)

    mock_sim = Mock()

    # Mock tax_benefit_system
    mock_sim.tax_benefit_system = create_mock_tax_benefit_system()

    # Mock calculate to return different values based on variable and map_to
    def mock_calculate(variable_name, map_to=None, period=None):
        result = Mock()
        if variable_name == "place_fips":
            if map_to == "person":
                result.values = np.array(person_place_fips)
            else:
                result.values = np.array(place_fips_values)
        elif variable_name == "person_id":
            result.values = np.array(person_ids)
        elif variable_name == "household_id":
            if map_to == "person":
                result.values = np.array(person_household_ids)
            else:
                result.values = np.array(household_ids)
        elif variable_name in ["tax_unit_id", "spm_unit_id", "family_id", "marital_unit_id"]:
            # For simplicity, use household_id as proxy for other entity IDs
            if map_to == "person":
                result.values = np.array(person_household_ids)
            else:
                result.values = np.array(household_ids)
        else:
            result.values = np.array([])
        return result

    mock_sim.calculate = mock_calculate

    # Mock to_input_dataframe to return person-level DataFrame
    df = pd.DataFrame({
        "person_id__2024": person_ids,
        "household_id__2024": person_household_ids,
        "place_fips__2024": person_place_fips,
    })
    mock_sim.to_input_dataframe.return_value = df

    return mock_sim


def create_mock_simulation_with_bytes_place_fips(
    place_fips_values: list[bytes],
    household_ids: list[int] | None = None,
    persons_per_household: int = 1,
) -> Mock:
    """Create a mock simulation with bytes place_fips data (as from HDF5).

    Args:
        place_fips_values: List of place FIPS codes as bytes.
        household_ids: Optional list of household IDs.
        persons_per_household: Number of persons per household (default 1).

    Returns:
        Mock simulation object configured for entity_rel filtering.
    """
    if household_ids is None:
        household_ids = list(range(len(place_fips_values)))

    num_households = len(place_fips_values)
    num_persons = num_households * persons_per_household

    person_ids = list(range(num_persons))
    person_household_ids = []
    person_place_fips = []
    for i, (hh_id, place) in enumerate(zip(household_ids, place_fips_values)):
        for _ in range(persons_per_household):
            person_household_ids.append(hh_id)
            person_place_fips.append(place)

    mock_sim = Mock()
    mock_sim.tax_benefit_system = create_mock_tax_benefit_system()

    def mock_calculate(variable_name, map_to=None, period=None):
        result = Mock()
        if variable_name == "place_fips":
            if map_to == "person":
                result.values = np.array(person_place_fips)
            else:
                result.values = np.array(place_fips_values)
        elif variable_name == "person_id":
            result.values = np.array(person_ids)
        elif variable_name == "household_id":
            if map_to == "person":
                result.values = np.array(person_household_ids)
            else:
                result.values = np.array(household_ids)
        elif variable_name in ["tax_unit_id", "spm_unit_id", "family_id", "marital_unit_id"]:
            if map_to == "person":
                result.values = np.array(person_household_ids)
            else:
                result.values = np.array(household_ids)
        else:
            result.values = np.array([])
        return result

    mock_sim.calculate = mock_calculate

    df = pd.DataFrame({
        "person_id__2024": person_ids,
        "household_id__2024": person_household_ids,
        "place_fips__2024": person_place_fips,
    })
    mock_sim.to_input_dataframe.return_value = df

    return mock_sim


def create_mock_simulation_type() -> Mock:
    """Create a mock simulation type class.

    Returns:
        Mock that can be called to create simulation instances.
    """
    mock_simulation_type = Mock()
    mock_simulation_type.return_value = Mock()
    return mock_simulation_type


def create_simulation_instance():
    """Create a Simulation instance without calling __init__.

    Returns:
        A bare Simulation instance for testing methods directly.
    """
    from policyengine.simulation import Simulation

    return object.__new__(Simulation)


# =============================================================================
# Pytest Fixtures - Pre-configured Mocks
# =============================================================================


@pytest.fixture
def mock_simulation_type() -> Mock:
    """Fixture for a mock simulation type class."""
    return create_mock_simulation_type()


@pytest.fixture
def mock_reform() -> Mock:
    """Fixture for a mock reform object."""
    return Mock(name="mock_reform")


@pytest.fixture
def simulation_instance():
    """Fixture for a bare Simulation instance."""
    return create_simulation_instance()


@pytest.fixture
def mock_sim_mixed_places() -> Mock:
    """Mock simulation with mixed places including Paterson."""
    return create_mock_simulation_with_place_fips(MIXED_PLACES_WITH_PATERSON)


@pytest.fixture
def mock_sim_no_paterson() -> Mock:
    """Mock simulation with no Paterson households."""
    return create_mock_simulation_with_place_fips(PLACES_WITHOUT_PATERSON)


@pytest.fixture
def mock_sim_all_paterson() -> Mock:
    """Mock simulation where all households are in Paterson."""
    return create_mock_simulation_with_place_fips(ALL_PATERSON_PLACES)


@pytest.fixture
def mock_sim_bytes_places() -> Mock:
    """Mock simulation with bytes-encoded place FIPS (HDF5 style)."""
    return create_mock_simulation_with_bytes_place_fips(MIXED_PLACES_BYTES)


@pytest.fixture
def mock_sim_multiple_nj_places() -> Mock:
    """Mock simulation with multiple NJ places."""
    return create_mock_simulation_with_place_fips(MULTIPLE_NJ_PLACES)


@pytest.fixture
def mock_sim_for_reform_test() -> Mock:
    """Mock simulation for testing reform passthrough."""
    return create_mock_simulation_with_place_fips(TWO_PLACES_FOR_REFORM_TEST)


# =============================================================================
# Pytest Fixtures - Dataset Fixtures
# =============================================================================


@pytest.fixture
def mini_place_dataset() -> pd.DataFrame:
    """Create a mini dataset with place_fips for testing.

    Simulates 10 households across 3 NJ places:
    - Paterson (57000): 4 households (IDs: 0, 1, 4, 7)
    - Newark (51000): 3 households (IDs: 2, 5, 8)
    - Jersey City (36000): 3 households (IDs: 3, 6, 9)

    Returns:
        DataFrame with household_id, place_fips, household_weight,
        and household_net_income columns.
    """
    return pd.DataFrame(
        {
            "household_id": list(range(10)),
            "place_fips": [
                NJ_PATERSON_FIPS,
                NJ_PATERSON_FIPS,
                NJ_NEWARK_FIPS,
                NJ_JERSEY_CITY_FIPS,
                NJ_PATERSON_FIPS,
                NJ_NEWARK_FIPS,
                NJ_JERSEY_CITY_FIPS,
                NJ_PATERSON_FIPS,
                NJ_NEWARK_FIPS,
                NJ_JERSEY_CITY_FIPS,
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


@pytest.fixture
def mini_place_dataset_with_bytes() -> pd.DataFrame:
    """Create a mini dataset with bytes place_fips (as from HDF5).

    Simulates 4 households across 2 NJ places with bytes-encoded FIPS:
    - Paterson (b"57000"): 2 households (IDs: 0, 1)
    - Newark (b"51000"): 2 households (IDs: 2, 3)

    Returns:
        DataFrame with household_id, place_fips (as bytes), and household_weight.
    """
    return pd.DataFrame(
        {
            "household_id": [0, 1, 2, 3],
            "place_fips": [
                NJ_PATERSON_FIPS_BYTES,
                NJ_PATERSON_FIPS_BYTES,
                NJ_NEWARK_FIPS_BYTES,
                NJ_NEWARK_FIPS_BYTES,
            ],
            "household_weight": [1000.0, 1000.0, 1000.0, 1000.0],
        }
    )
