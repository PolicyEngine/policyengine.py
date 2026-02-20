"""UK parliamentary constituency impact output class.

Computes per-constituency income changes using pre-computed weight matrices.
Each constituency has a row in the weight matrix (shape: 650 x N_households)
that reweights all households to represent that constituency's demographics.
"""

from typing import TYPE_CHECKING

import h5py
import numpy as np
import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class ConstituencyImpact(Output):
    """Per-parliamentary-constituency income change from a UK policy reform.

    Uses pre-computed weight matrices from GCS to reweight households
    for each of 650 constituencies, then computes weighted average and
    relative household income changes.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    weight_matrix_path: str
    constituency_csv_path: str
    year: str = "2025"

    # Results populated by run()
    constituency_results: list[dict] | None = None

    def run(self) -> None:
        """Load weight matrix and compute per-constituency metrics."""
        # Load constituency metadata (code, name, x, y)
        constituency_df = pd.read_csv(self.constituency_csv_path)

        # Load weight matrix: shape (N_constituencies, N_households)
        with h5py.File(self.weight_matrix_path, "r") as f:
            weight_matrix = f[self.year][...]

        # Get household income arrays from output datasets
        baseline_hh = self.baseline_simulation.output_dataset.data.household
        reform_hh = self.reform_simulation.output_dataset.data.household

        baseline_income = baseline_hh["household_net_income"].values
        reform_income = reform_hh["household_net_income"].values

        results: list[dict] = []
        for i in range(len(constituency_df)):
            row = constituency_df.iloc[i]
            code = str(row["code"])
            name = str(row["name"])
            x = int(row["x"])
            y = int(row["y"])
            w = weight_matrix[i]

            total_weight = float(np.sum(w))
            if total_weight == 0:
                continue

            weighted_baseline = float(np.sum(baseline_income * w))
            weighted_reform = float(np.sum(reform_income * w))

            # Count of weighted households
            count = float(np.sum(w > 0))
            if count == 0:
                continue

            avg_change = (weighted_reform - weighted_baseline) / total_weight
            rel_change = (
                (weighted_reform / weighted_baseline - 1.0)
                if weighted_baseline != 0
                else 0.0
            )

            results.append(
                {
                    "constituency_code": code,
                    "constituency_name": name,
                    "x": x,
                    "y": y,
                    "average_household_income_change": float(avg_change),
                    "relative_household_income_change": float(rel_change),
                    "population": total_weight,
                }
            )

        self.constituency_results = results


def compute_uk_constituency_impacts(
    baseline_simulation: "Simulation",
    reform_simulation: "Simulation",
    weight_matrix_path: str,
    constituency_csv_path: str,
    year: str = "2025",
) -> ConstituencyImpact:
    """Compute per-constituency income changes for UK.

    Args:
        baseline_simulation: Completed baseline simulation.
        reform_simulation: Completed reform simulation.
        weight_matrix_path: Path to parliamentary_constituency_weights.h5.
        constituency_csv_path: Path to constituencies_2024.csv.
        year: Year key in the H5 file (default "2025").

    Returns:
        ConstituencyImpact with constituency_results populated.
    """
    impact = ConstituencyImpact(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        weight_matrix_path=weight_matrix_path,
        constituency_csv_path=constituency_csv_path,
        year=year,
    )
    impact.run()
    return impact
