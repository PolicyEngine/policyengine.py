from __future__ import annotations

from typing import Dict

import pandas as pd

from policyengine.models.dataset import Dataset
from policyengine.models.single_year_dataset import SingleYearDataset


def create_ecps(year=2024) -> Dataset:
    """Create the ECPS 2024 dataset using the US microsimulation variables.

    Builds per-entity tables from policyengine_us for the 2024 period.
    """
    from policyengine_us import Microsimulation

    sim = Microsimulation()
    tables: Dict[str, pd.DataFrame] = {}

    for entity in sim.tax_benefit_system.entities_by_singular().keys():
        for variable in sim.tax_benefit_system.variables:
            if sim.tax_benefit_system.variables[variable].entity.key != entity:
                continue
            known_periods = map(str, sim.get_known_periods(variable))
            if "2024" in known_periods: # Data loaded in 2024
                tables[entity] = tables.get(entity, pd.DataFrame())
                tables[entity][variable] = sim.calculate(variable, period=year)

    data = SingleYearDataset(tables=tables, year=year)
    return Dataset(name="ECPS 2024", data=data, dataset_type="us")


def create_us_synthetic(year: int = 2024) -> Dataset:
    """Create a synthetic US dataset with realistic structure for demonstrations.

    Creates diverse households to demonstrate tax and benefit policy impacts.
    """
    # Create diverse household compositions
    household = pd.DataFrame({
        "household_id": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        "state_fips": [6, 36, 48, 12, 17, 42, 4, 53, 25, 13],  # CA, NY, TX, FL, IL, PA, AZ, WA, MA, GA
        "household_weight": [1.0] * 10,
        "tenure_type": ["OWNER", "RENTER", "OWNER", "RENTER", "OWNER", 
                       "RENTER", "OWNER", "RENTER", "OWNER", "RENTER"],
    })
    
    # SPM units (supplemental poverty measure units)
    spm_unit = pd.DataFrame({
        "spm_unit_id": [1301, 1302, 1303, 1304, 1305, 1306, 1307, 1308, 1309, 1310],
        "snap_reported": [0, 0, 400, 600, 800, 0, 300, 0, 0, 200],  # SNAP benefits
        "housing_assistance": [0, 0, 500, 800, 1000, 0, 400, 0, 0, 300],
        "spm_unit_pre_subsidy_childcare_expenses": [0, 8000, 0, 6000, 0, 0, 5000, 10000, 0, 4000],
    })
    
    # Families
    family = pd.DataFrame({
        "family_id": [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010]
    })
    
    # Tax units (can have multiple per household)
    tax_unit = pd.DataFrame({
        "tax_unit_id": list(range(1201, 1213)),  # 12 tax units across 10 households
        "takes_up_eitc": [True] * 12,
        "takes_up_dc_ptc": [True] * 12,
        "cdcc_relevant_expenses": [0, 3000, 0, 2500, 0, 0, 4000, 5000, 0, 2000, 0, 0],
    })
    
    # Marital units
    marital_unit = pd.DataFrame({
        "marital_unit_id": list(range(1101, 1118))  # 17 marital units
    })
    
    # Person data with diverse characteristics
    person = pd.DataFrame({
        "person_id": list(range(1, 31)),  # 30 people
        "person_household_id": [
            100, 100, 100, 100,  # Family with 2 children
            101, 101,            # Working couple
            102,                 # Single elderly
            103, 103, 103,       # Single parent with 2 kids
            104, 104, 104, 104,  # Low income family
            105,                 # High earner
            106, 106,            # Disabled couple
            107, 107, 107, 107, 107,  # Large family
            108, 108,            # DINK (dual income no kids)
            109, 109, 109,       # Middle income family
            101, 103, 104,       # Additional people in some households (3 people to make 30 total)
        ],
        "person_spm_unit_id": [
            1301, 1301, 1301, 1301,
            1302, 1302,
            1303,
            1304, 1304, 1304,
            1305, 1305, 1305, 1305,
            1306,
            1307, 1307,
            1308, 1308, 1308, 1308, 1308,
            1309, 1309,
            1310, 1310, 1310,
            1302, 1304, 1305,
        ],
        "person_family_id": [
            1001, 1001, 1001, 1001,
            1002, 1002,
            1003,
            1004, 1004, 1004,
            1005, 1005, 1005, 1005,
            1006,
            1007, 1007,
            1008, 1008, 1008, 1008, 1008,
            1009, 1009,
            1010, 1010, 1010,
            1002, 1004, 1005,
        ],
        "person_tax_unit_id": [
            1201, 1201, 1201, 1201,
            1202, 1202,
            1203,
            1204, 1204, 1204,
            1205, 1205, 1205, 1205,
            1206,
            1207, 1207,
            1208, 1208, 1209, 1209, 1209,  # Large family has 2 tax units
            1210, 1210,
            1211, 1211, 1211,
            1202, 1204, 1205,
        ],
        "person_marital_unit_id": [
            1101, 1101, 1102, 1103,
            1104, 1104,
            1105,
            1106, 1107, 1108,
            1109, 1109, 1110, 1111,
            1112,
            1113, 1113,
            1114, 1114, 1115, 1116, 1117,
            1104, 1104,
            1109, 1109, 1110,
            1104, 1106, 1109,
        ],
        "age": [35, 33, 8, 5, 42, 40, 68, 38, 12, 9, 32, 30, 4, 2,
                55, 45, 43, 41, 39, 14, 10, 7, 35, 34, 44, 42, 6, 16, 10, 1],
        "employment_income": [
            30000, 25000, 0, 0,  # Parents working
            55000, 48000,        # High earners
            0,                   # Retired
            22000, 0, 0,         # Single parent
            15000, 12000, 0, 0,  # Low income
            150000,              # Very high earner
            0, 0,                # Disabled
            35000, 32000, 0, 0, 0,  # Parents in large family
            70000, 65000,        # DINK
            45000, 38000, 0,     # Middle income
            0, 0, 0,             # Additional dependents (3 people)
        ],
        "social_security": [
            0, 0, 0, 0,
            0, 0,
            18000,  # Elderly SS
            0, 0, 0,
            0, 0, 0, 0,
            0,
            12000, 11000,  # Disabled SS
            0, 0, 0, 0, 0,
            0, 0,
            0, 0, 0,
            0, 0, 0,  # 3 additional people
        ],
        "self_employment_income": [
            0, 8000, 0, 0,  # One parent self-employed
            0, 0,
            0,
            5000, 0, 0,  # Single parent self-employed
            0, 0, 0, 0,
            0,
            0, 0,
            10000, 0, 0, 0, 0,  # One parent self-employed
            0, 0,
            0, 6000, 0,  # One parent self-employed
            0, 0, 0,  # 3 additional people
        ],
        "is_disabled": [
            False, False, False, False,
            False, False,
            False,
            False, False, False,
            False, False, False, False,
            False,
            True, True,  # Disabled couple
            False, False, True, False, False,  # One disabled child
            False, False,
            False, False, False,
            False, False, False,  # 3 additional people
        ],
    })
    
    data = SingleYearDataset(
        tables={
            "person": person,
            "marital_unit": marital_unit,
            "tax_unit": tax_unit,
            "family": family,
            "spm_unit": spm_unit,
            "household": household,
        },
        year=year,
    )
    return Dataset(name="us-synthetic", data=data, dataset_type="us")

