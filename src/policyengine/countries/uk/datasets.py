from __future__ import annotations

from typing import Dict

import pandas as pd

from policyengine.models.dataset import Dataset
from policyengine.models.single_year_dataset import SingleYearDataset


def create_efrs(year: int = 2029) -> Dataset:
    """Create the UK EFRS dataset for a given year (default 2029).

    Uses the policyengine_uk Microsimulation’s bundled dataset tables.
    """
    from policyengine_uk import Microsimulation

    sim = Microsimulation()
    data = SingleYearDataset(
        tables=dict(
            person=sim.dataset[year].person,
            benunit=sim.dataset[year].benunit,
            household=sim.dataset[year].household,
        ),
        year=year,
    )
    return Dataset(name="efrs", data=data, dataset_type="uk")


def create_uk_synthetic(year: int = 2029) -> Dataset:
    """Create a small synthetic UK dataset with minimal structure.

    Tables: person, benunit, household; includes required ID columns.
    """
    # IDs
    person = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5],
            "person_benunit_id": [10, 10, 20, 20, 30],
            "person_household_id": [100, 100, 200, 200, 300],
        }
    )
    benunit = pd.DataFrame({"benunit_id": [10, 20, 30]})
    household = pd.DataFrame(
        {
            "household_id": [100, 200, 300],
            # Simple weight or income columns for examples
            "household_weight": [1.0, 0.8, 1.2],
            "market_income": [40_000, 60_000, 20_000],
        }
    )

    data = SingleYearDataset(
        tables={"person": person, "benunit": benunit, "household": household},
        year=year,
    )
    return Dataset(name="uk-synthetic", data=data, dataset_type="uk")

