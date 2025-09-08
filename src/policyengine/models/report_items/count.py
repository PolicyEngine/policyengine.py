from __future__ import annotations

from typing import Any

import pandas as pd

try:
    from microdf import MicroDataFrame

    MICRODF_AVAILABLE = True
except ImportError:
    MICRODF_AVAILABLE = False
    MicroDataFrame = None

from policyengine.models.simulation import Simulation  # ensure fwd ref
from policyengine.models.single_year_dataset import SingleYearDataset
from .base import ReportElementDataItem


class Count(ReportElementDataItem):
    """Weighted count of entities where a variable matches a condition.

    Use `Count.run([...])` with items initialized with `count=None`.
    Conditions supported: exact equality via `equals_value`, and/or range via
    `min_value` (inclusive) and `max_value` (exclusive). If `equals_value` is
    provided, range bounds are applied in addition (logical AND).
    """

    simulation: "Simulation"
    time_period: int | str | None = None
    variable: str
    entity_level: str = "person"
    equals_value: Any | None = None
    min_value: float | None = None
    max_value: float | None = None
    count: float | None = None

    @staticmethod
    def run(items: list["Count"]) -> list["Count"]:
        if not items:
            return []

        # Group items by entity level to reuse the same table
        by_level: dict[str, list[Count]] = {}
        for it in items:
            by_level.setdefault(it.entity_level, []).append(it)

        out: list[Count] = []
        for entity_level, group in by_level.items():
            sim = group[0].simulation
            data: SingleYearDataset = sim.result.data  # type: ignore[attr-defined]
            table: pd.DataFrame = data.tables[entity_level]
            time_period = getattr(sim.dataset.data, "year", None)
            use_weights = "weight_value" in table.columns

            for it in group:
                # Check if variable is in current entity's columns
                if it.variable in table.columns:
                    series = table[it.variable]
                else:
                    # Variable is on a different entity level
                    # Try to find it in other entity tables and map via foreign keys
                    series = None
                    for other_entity, other_table in data.tables.items():
                        if other_entity != entity_level and it.variable in other_table.columns:
                            # Found the variable in another entity
                            # Check if we have a foreign key relationship
                            fk_col = f"{entity_level}_{other_entity}_id"
                            if fk_col in table.columns:
                                # Map variable from other entity to current entity
                                other_df = other_table.set_index(f"{other_entity}_id")
                                series = pd.Series(
                                    other_df.loc[table[fk_col], it.variable].values,
                                    index=table.index
                                )
                                break
                    
                    if series is None:
                        # Could not find variable or foreign key relationship
                        # Use empty mask to count nothing
                        series = pd.Series(float('nan'), index=table.index)
                
                mask = pd.Series(True, index=table.index)
                if it.equals_value is not None:
                    mask &= series == it.equals_value
                if it.min_value is not None:
                    mask &= series >= it.min_value
                if it.max_value is not None:
                    mask &= series < it.max_value
                df = table.loc[mask].copy()
                df["__ones__"] = 1.0
                if not MICRODF_AVAILABLE:
                    raise ImportError(
                        "microdf is not installed. "
                        "Install it with: pip install 'policyengine[core]'"
                    )
                mdf = (
                    MicroDataFrame(df, weights="weight_value")
                    if use_weights and "weight_value" in df.columns
                    else MicroDataFrame(df)
                )
                cnt = float(mdf["__ones__"].sum())

                payload = it.model_dump()
                payload.update({"time_period": time_period, "count": cnt})
                out.append(Count(**payload))

        return out
