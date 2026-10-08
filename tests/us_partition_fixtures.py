"""A synthetic native US input file; never a substitute for certified data."""

from pathlib import Path

import pandas as pd

from policyengine.countries.us.data.states import US_STATE_FIPS
from policyengine.provenance.dataset_materialization import MaterializedDataset
from policyengine.tax_benefit_models.us.datasets import US_ENTITY_KEYS
from policyengine.utils.hashing import sha256_file


def write_source(path: Path, *, include_nulls: bool = False) -> MaterializedDataset:
    states = list(US_STATE_FIPS.items())
    ids = list(range(100, 100 + len(states)))
    frames = {entity: pd.DataFrame({f"{entity}_id": ids}) for entity in US_ENTITY_KEYS}
    person = frames["person"]
    for entity in US_ENTITY_KEYS:
        if entity != "person":
            person[f"person_{entity}_id"] = ids
    person["age"] = 40
    person["employment_income"] = 40000.0
    person["is_tax_unit_head"] = True
    # Certified inputs still use this legacy name. Both preparation paths must
    # preserve the draw under its current model name, including later years.
    person["would_claim_wic"] = [index % 2 == 0 for index in range(len(ids))]
    household = frames["household"]
    household["household_weight"] = [float(index + 1) for index in range(len(ids))]
    household["state_fips"] = [fips for _, fips in states]
    household["congressional_district_geoid"] = [fips * 100 + 1 for _, fips in states]
    if include_nulls:
        household["fixture_nullable_float"] = [None] + [1.5] * (len(ids) - 1)
        household["fixture_mixed_object"] = pd.Series(
            [None, 7, "text"] + ["x"] * (len(ids) - 3), dtype=object
        )
    with pd.HDFStore(path, "w") as store:
        for entity, frame in frames.items():
            store.put(entity, frame.sample(frac=1, random_state=42), format="fixed")
        store.put("_time_period", pd.Series([2024]), format="fixed")
        store.put("_fixture_metadata", pd.Series(["preserve-me"]), format="fixed")
    return MaterializedDataset(
        data_package_name="synthetic-fixture",
        repo_type="dataset",
        revision="fixture",
        source_uri="fixture://us-inputs",
        sha256=sha256_file(path),
        path=path,
    )
