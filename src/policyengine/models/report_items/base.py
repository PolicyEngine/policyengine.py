from __future__ import annotations

from typing import Iterable

import pandas as pd
from pydantic import BaseModel

from policyengine.models.simulation import Simulation


class ReportElementDataItem(BaseModel):
    """Base class for report element output records.

    Provides a generic helper to convert lists of records to DataFrames.
    """

    @classmethod
    def to_dataframe(
        cls, records: Iterable["ReportElementDataItem"]
    ) -> pd.DataFrame:
        """Convert records to a DataFrame.

        Default rule: if a field is a Simulation, replace it with columns for
        policy/dataset/dynamic names. For fields named `baseline_simulation`
        or `reform_simulation`, prefix these columns with `baseline_`/`reform_`.
        For a field named exactly `simulation`, use unprefixed `policy`, `dataset`,
        and `dynamic`.
        """
        rows = []
        for r in records:
            row: dict[str, object] = {}
            for k in getattr(r, "model_fields").keys():
                v = getattr(r, k)
                if isinstance(v, Simulation):
                    if k == "simulation":
                        prefix = ""
                    elif k.endswith("_simulation"):
                        prefix = k[: -len("_simulation")] + "_"
                    else:
                        prefix = k + "_"
                    row[prefix + "policy"] = getattr(
                        getattr(v, "policy", None), "name", None
                    )
                    row[prefix + "dataset"] = getattr(
                        getattr(v, "dataset", None), "name", None
                    )
                    row[prefix + "dynamic"] = getattr(
                        getattr(v, "dynamic", None), "name", None
                    )
                else:
                    row[k] = v
            rows.append(row)
        return pd.DataFrame(rows)

    @property
    def dataframe(self) -> pd.DataFrame:
        """A single-row DataFrame representation of this record."""
        return pd.DataFrame([self.model_dump()])
