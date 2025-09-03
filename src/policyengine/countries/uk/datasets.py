from __future__ import annotations

from typing import Dict

import pandas as pd

from policyengine.models.dataset import Dataset
from policyengine.models.single_year_dataset import SingleYearDataset
from policyengine.models.enums import DatasetType

def create_efrs_years(start_year: int, end_year: int) -> list[Dataset]:
    """Create the UK EFRS datasets for a range of years."""
    from policyengine_uk import Microsimulation

    sim = Microsimulation()
    return [create_efrs(year=year, sim=sim) for year in range(start_year, end_year + 1)]


def create_efrs(year: int = 2029, sim: "Microsimulation" | None = None) -> Dataset:
    """Create the UK EFRS dataset for a given year (default 2029).

    Uses the policyengine_uk Microsimulation’s bundled dataset tables.
    """
    if sim is None:
        from policyengine_uk import Microsimulation
        sim = Microsimulation()
    tables = dict(
        person=getattr(sim.dataset[year], "person", None),
        benunit=getattr(sim.dataset[year], "benunit", getattr(sim.dataset[year], "benefit_unit", None)),
        household=getattr(sim.dataset[year], "household", None),
    )
    # Drop any missing tables to avoid serialising Nones
    tables = {k: v for k, v in tables.items() if v is not None}
    data = SingleYearDataset(
        tables=tables,
        year=year,
    )
    return Dataset(name=f"efrs_{year}", data=data, dataset_type=DatasetType.UK)


def create_uk_synthetic(year: int = 2029) -> Dataset:
    """Create a synthetic UK dataset with realistic structure for demonstrations.

    Creates households with diverse characteristics to demonstrate policy impacts.
    """
    # Create 10 diverse households with different compositions
    household_ids = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    benunit_ids = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    
    # Person data: various ages, employment, and benefit situations
    person = pd.DataFrame(
        {
            "person_id": list(range(1, 25)),
            "person_benunit_id": [
                10, 10, 10, 10,  # Family with 2 children
                11, 11,          # Working couple
                12,              # Single pensioner
                13, 13, 13,      # Single parent with 2 children
                14, 14,          # Disabled couple
                15,              # High earner
                16, 16,          # Low income couple
                17, 17, 17, 17,  # Large family
                18,              # Young professional
                19, 19, 19, 19,  # Middle income family (added 1 more person)
            ],
            "person_household_id": [
                100, 100, 100, 100,  # Family household
                101, 101,            # Working couple household
                102,                 # Single pensioner
                103, 103, 103,       # Single parent household
                104, 104,            # Disabled couple
                105,                 # High earner
                106, 106,            # Low income couple
                107, 107, 107, 107,  # Large family
                108,                 # Young professional
                109, 109, 109, 109,  # Middle income family (added 1 more person)
            ],
            "age": [35, 33, 8, 5, 42, 40, 68, 38, 12, 9, 45, 43, 52, 28, 25,
                   40, 38, 14, 10, 6, 30, 44, 42, 7],
            "employment_income": [
                25000, 20000, 0, 0,  # Parents working, children none
                45000, 38000,        # Both working
                0,                   # Pensioner
                18000, 0, 0,         # Single parent working
                0, 0,                # Disabled
                120000,              # High earner
                12000, 8000,         # Low income
                32000, 28000, 0, 0,  # Parents working
                35000,               # Young professional
                40000, 30000, 0, 0,  # Middle income (added child with 0 income)
            ],
            "pension_income": [
                0, 0, 0, 0,
                0, 0,
                15000,  # Pensioner
                0, 0, 0,
                0, 0,
                0,
                0, 0,
                0, 0, 0, 0,
                0,
                0, 0, 0, 0,  # Added one more 0
            ],
            "self_employment_income": [
                0, 5000, 0, 0,  # One parent has some self-employment
                0, 0,
                0,
                3000, 0, 0,  # Single parent has some self-employment
                0, 0,
                0,
                0, 0,
                8000, 0, 0, 0,  # One parent self-employed
                0,
                0, 0, 0, 0,  # Added one more 0
            ],
            "is_disabled": [
                False, False, False, False,
                False, False,
                False,
                False, False, False,
                True, True,  # Disabled couple
                False,
                False, False,
                False, False, True, False,  # One disabled child
                False,
                False, False, False, False,  # Added one more False
            ],
            "dla_m_reported": [  # Disability living allowance mobility
                0, 0, 0, 0,
                0, 0,
                0,
                0, 0, 0,
                400, 400,  # Disabled couple
                0,
                0, 0,
                0, 0, 300, 0,  # Disabled child
                0,
                0, 0, 0, 0,  # Added one more 0
            ],
            "dla_sc_reported": [  # Disability living allowance self-care
                0, 0, 0, 0,
                0, 0,
                0,
                0, 0, 0,
                600, 600,  # Disabled couple
                0,
                0, 0,
                0, 0, 450, 0,  # Disabled child
                0,
                0, 0, 0, 0,  # Added one more 0
            ],
        }
    )
    
    benunit = pd.DataFrame(
        {
            "benunit_id": benunit_ids,
            "would_claim_uc": [True] * 10,  # All would claim if eligible
            "would_claim_pc": [False, False, True, True, True, False, True, True, False, False],
            "would_claim_child_benefit": [True, False, False, True, False, False, False, True, False, True],
        }
    )
    
    household = pd.DataFrame(
        {
            "household_id": household_ids,
            "council_tax": [1400, 1600, 1200, 1300, 1400, 2500, 1100, 1500, 1200, 1700],
            "rent": [800, 1200, 600, 750, 900, 0, 500, 950, 900, 0],  # Some own homes (rent=0)
            "household_weight": [1.0] * 10,  # Equal weights for simplicity
            "region": [
                "LONDON", "SOUTH_EAST", "NORTH_WEST", "SCOTLAND", "WALES",
                "LONDON", "NORTH_EAST", "EAST_MIDLANDS", "SOUTH_WEST", "WEST_MIDLANDS"
            ],
            "tenure_type": [
                "RENT_PRIVATELY", "RENT_PRIVATELY", "RENT_FROM_LA", 
                "RENT_FROM_HA", "RENT_PRIVATELY", "OWNED_OUTRIGHT",
                "RENT_FROM_LA", "RENT_PRIVATELY", "RENT_PRIVATELY", "OWNED_WITH_MORTGAGE"
            ],
        }
    )

    data = SingleYearDataset(
        tables={"person": person, "benunit": benunit, "household": household},
        year=year,
    )
    return Dataset(name="uk-synthetic", data=data, dataset_type="uk")
