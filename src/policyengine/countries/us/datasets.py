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
    """Create a small synthetic US dataset with required structure.

    Tables: person, marital_unit, tax_unit, family, spm_unit, household.
    Includes required ID columns with consistent foreign keys.
    """
    # Core entity IDs
    household = pd.DataFrame({"household_id": [100, 200, 300]})
    family = pd.DataFrame({"family_id": [1001, 2001, 3001]})
    marital_unit = pd.DataFrame({"marital_unit_id": [1101, 2201, 3301]})
    tax_unit = pd.DataFrame({"tax_unit_id": [1201, 2202, 3303]})
    spm_unit = pd.DataFrame({"spm_unit_id": [1301, 2302, 3304]})

    # Person links to each entity via person_{entity}_id
    person = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5],
            "person_household_id": [100, 100, 200, 200, 300],
            "person_family_id": [1001, 1001, 2001, 2001, 3001],
            "person_marital_unit_id": [1101, 1101, 2201, 2201, 3301],
            "person_tax_unit_id": [1201, 1201, 2202, 2202, 3303],
            "person_spm_unit_id": [1301, 1301, 2302, 2302, 3304],
        }
    )

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

