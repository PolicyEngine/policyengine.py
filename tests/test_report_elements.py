from __future__ import annotations

import pandas as pd

from policyengine.models import Dataset, DatasetType, Policy, Dynamic
from policyengine.models.single_year_dataset import SingleYearDataset
from policyengine.models.simulation import Simulation
from policyengine.models.report_items import Aggregate, AggregateMetric


def _mk_sim_with_person_table(
    df: pd.DataFrame, year: int = 2025
) -> Simulation:
    syd = SingleYearDataset(tables={"person": df}, year=year)
    ds = Dataset(name="ds", data=syd, dataset_type=DatasetType.UK)
    sim = Simulation(
        dataset=ds,
        policy=Policy(),
        dynamic=Dynamic(),
        country="uk",
    )
    # result mirrors dataset for reporting
    sim.result = Dataset(dataset_type=DatasetType.UK, data=syd)
    return sim


def test_aggregate_report_element_grouped_mean():
    df = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4],
            "race_ethnicity": ["A", "A", "B", "B"],
            "is_in_poverty": [0, 1, 1, 1],
            "weight_value": [1.0, 3.0, 1.0, 1.0],
        }
    )

    sim = _mk_sim_with_person_table(df)
    records = Aggregate.build(
        simulation=sim,
        variable="is_in_poverty",
        entity_level="person",
        filter_variable="race_ethnicity",
        metric=AggregateMetric.MEAN,
    )
    assert isinstance(records, list) and all(
        isinstance(r, type(records[0])) for r in records
    )
    # Expect two groups A and B
    assert len(records) == 2

    # Weighted mean poverty for A: (0*1 + 1*3) / (1+3) = 0.75
    # For B: (1*1 + 1*1) / (1+1) = 1.0
    df_out = Aggregate.to_dataframe(records).set_index("filter_variable_value")
    assert abs(df_out.loc["A", "value"] - 0.75) < 1e-9
    assert abs(df_out.loc["B", "value"] - 1.0) < 1e-9


def test_to_dataframe_flattens_simulation_columns():
    df = pd.DataFrame(
        {
            "person_id": [1, 2],
            "var": [10, 20],
            "weight_value": [1.0, 1.0],
        }
    )
    sim = _mk_sim_with_person_table(df)
    sim.policy.name = "P"
    sim.dataset.name = "D"
    sim.dynamic.name = "X"

    recs = Aggregate.build(simulation=sim, variable="var")
    dfx = Aggregate.to_dataframe(recs)
    # Simulation column is flattened to policy/dataset/dynamic
    assert "simulation" not in dfx.columns
    assert set(["policy", "dataset", "dynamic"]).issubset(dfx.columns)
