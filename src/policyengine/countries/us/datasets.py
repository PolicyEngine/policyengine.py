from __future__ import annotations

from typing import Dict

import pandas as pd

from policyengine.models.dataset import Dataset
from policyengine.models.single_year_dataset import SingleYearDataset
from policyengine.models.enums import DatasetType

US_HUGGING_FACE_REPO = "policyengine/policyengine-us-data"
US_HUGGING_FACE_DATASETS = ["enhanced_cps_2024.h5"]


def create_dataset_years_from_hf(
    start_year: int,
    end_year: int,
    *,
    repo: str,
    filename: str,
    version: str | None = None,
) -> list[Dataset]:
    """Create ECPS datasets using a Hugging Face dataset file as the base year.

    Constructs a `Microsimulation` with `dataset="hf://{repo}/{filename}[@{version}]"`
    and then materialises dataset rows for the requested range.
    """
    try:
        from policyengine_us import Microsimulation
    except ImportError:
        raise ImportError(
            "policyengine-us is not installed. "
            "Install it with: pip install 'policyengine[us]' or pip install policyengine-us"
        )

    base = f"hf://{repo}/{filename}"
    if version:
        base = f"{base}@{version}"
    sim = Microsimulation(dataset=base)

    return [
        create_dataset(year=year, sim=sim, filename=filename)
        for year in range(start_year, end_year + 1)
    ]


def create_dataset(
    year: int = 2024,
    sim: "Microsimulation" | None = None,
    filename: str = None,
) -> Dataset:
    """Create the dataset for a given year using the US microsimulation.

    This computes variables per entity for the requested year. This is the
    original behavior and differs from the UK path.
    """
    if sim is None:
        try:
            from policyengine_us import Microsimulation
        except ImportError:
            raise ImportError(
                "policyengine-us is not installed. "
                "Install it with: pip install 'policyengine[us]' or pip install policyengine-us"
            )

        sim = Microsimulation()
    tables: Dict[str, pd.DataFrame] = {}

    for entity in sim.tax_benefit_system.entities_by_singular().keys():
        for variable in sim.tax_benefit_system.variables:
            if sim.tax_benefit_system.variables[variable].entity.key != entity:
                continue
            known_periods = set(map(str, sim.get_known_periods(variable)))
            if str(year) in known_periods:
                if entity not in tables:
                    tables[entity] = pd.DataFrame()
                tables[entity][variable] = sim.calculate(variable, period=year)

    data = SingleYearDataset(tables=tables, year=year)
    return Dataset(
        name=filename.replace(".h5", "") + f"/{year}",
        data=data,
        dataset_type=DatasetType.US_SINGLE_YEAR,
    )
