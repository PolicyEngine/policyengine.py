"""UK local authority impact output class.

Computes per-local-authority income changes using pre-computed weight matrices.
Each local authority has a row in the weight matrix (shape: 360 x N_households)
that reweights all households to represent that local authority's demographics.
"""

from typing import TYPE_CHECKING

import h5py
import numpy as np
import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class LocalAuthorityImpact(Output):
    """Per-local-authority income change from a UK policy reform.

    Uses pre-computed weight matrices from GCS to reweight households
    for each of 360 local authorities, then computes weighted average and
    relative household income changes.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    weight_matrix_path: str
    local_authority_csv_path: str
    year: str = "2025"

    # Results populated by run()
    local_authority_results: list[dict] | None = None

    def run(self) -> None:
        """Load weight matrix and compute per-local-authority metrics."""
        # Load local authority metadata (code, x, y, name)
        la_df = pd.read_csv(self.local_authority_csv_path)

        # Load weight matrix: shape (N_local_authorities, N_households)
        with h5py.File(self.weight_matrix_path, "r") as f:
            weight_matrix = f[self.year][...]

        # Get household income arrays from output datasets
        baseline_hh = self.baseline_simulation.output_dataset.data.household
        reform_hh = self.reform_simulation.output_dataset.data.household

        baseline_income = baseline_hh["household_net_income"].values
        reform_income = reform_hh["household_net_income"].values

        results: list[dict] = []
        for i in range(len(la_df)):
            row = la_df.iloc[i]
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
                    "local_authority_code": code,
                    "local_authority_name": name,
                    "x": x,
                    "y": y,
                    "average_household_income_change": float(avg_change),
                    "relative_household_income_change": float(rel_change),
                    "population": total_weight,
                }
            )

        self.local_authority_results = results


def compute_uk_local_authority_impacts(
    baseline_simulation: "Simulation",
    reform_simulation: "Simulation",
    weight_matrix_path: str,
    local_authority_csv_path: str,
    year: str = "2025",
) -> LocalAuthorityImpact:
    """Compute per-local-authority income changes for UK.

    Args:
        baseline_simulation: Completed baseline simulation.
        reform_simulation: Completed reform simulation.
        weight_matrix_path: Path to local_authority_weights.h5.
        local_authority_csv_path: Path to local_authorities_2021.csv.
        year: Year key in the H5 file (default "2025").

    Returns:
        LocalAuthorityImpact with local_authority_results populated.
    """
    impact = LocalAuthorityImpact(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        weight_matrix_path=weight_matrix_path,
        local_authority_csv_path=local_authority_csv_path,
        year=year,
    )
    impact.run()
    return impact
