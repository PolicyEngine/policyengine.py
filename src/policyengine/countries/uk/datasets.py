from __future__ import annotations

from typing import Dict

import pandas as pd

from policyengine.models.dataset import Dataset
from policyengine.models.single_year_dataset import SingleYearDataset
from policyengine.models.enums import DatasetType


def create_dataset_years_from_hf(
    start_year: int,
    end_year: int,
    *,
    repo: str,
    filename: str,
    version: str | None = None,
) -> list[Dataset]:
    """Create datasets using a Hugging Face dataset file as the base year.

    Constructs a `Microsimulation` with `dataset="hf://{repo}/{filename}[@{version}]"`
    and then materialises dataset rows for the requested range.
    """
    try:
        from policyengine_uk import Microsimulation
    except ImportError:
        raise ImportError(
            "policyengine-uk is not installed. "
            "Install it with: pip install 'policyengine[uk]' or pip install policyengine-uk"
        )

    base = f"hf://{repo}/{filename}"
    if version:
        base = f"{base}@{version}"
    sim = Microsimulation(dataset=base)
    return [
        create_dataset(year=year, sim=sim, filename=filename, version=version)
        for year in range(start_year, end_year + 1)
    ]


def create_dataset(
    year: int = 2029,
    sim: "Microsimulation" | None = None,
    filename: str = None,
    version: str | None = None,
) -> Dataset:
    """Create the UK dataset for a given year (default 2029).

    Uses the policyengine_uk Microsimulation’s bundled dataset tables.
    """
    if sim is None:
        try:
            from policyengine_uk import Microsimulation
        except ImportError:
            raise ImportError(
                "policyengine-uk is not installed. "
                "Install it with: pip install 'policyengine[uk]' or pip install policyengine-uk"
            )

        sim = Microsimulation()
    tables = dict(
        person=getattr(sim.dataset[year], "person", None),
        benunit=getattr(
            sim.dataset[year],
            "benunit",
            getattr(sim.dataset[year], "benefit_unit", None),
        ),
        household=getattr(sim.dataset[year], "household", None),
    )
    # Drop any missing tables to avoid serialising Nones
    tables = {k: v for k, v in tables.items() if v is not None}
    data = SingleYearDataset(
        tables=tables,
        year=year,
    )
    return Dataset(
        name=filename.replace(".h5", "") + f"/{year}",
        data=data,
        dataset_type=DatasetType.UK_SINGLE_YEAR,
        version=version,
    )
