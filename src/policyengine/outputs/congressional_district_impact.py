"""Congressional district impact output class for US policy reforms."""

from typing import TYPE_CHECKING

import numpy as np
from pydantic import ConfigDict

from policyengine.core import Output

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class CongressionalDistrictImpact(Output):
    """Per-congressional-district income change from a policy reform.

    Groups households by congressional_district_geoid (integer SSDD format
    where SS = state FIPS, DD = district number) and computes weighted
    average and relative household income changes per district.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"

    # Results populated by run()
    district_results: list[dict] | None = None

    def run(self) -> None:
        """Group households by geoid and compute per-district metrics."""
        baseline_hh = self.baseline_simulation.output_dataset.data.household
        reform_hh = self.reform_simulation.output_dataset.data.household

        geoids = baseline_hh["congressional_district_geoid"].values
        baseline_income = baseline_hh["household_net_income"].values
        reform_income = reform_hh["household_net_income"].values
        weights = baseline_hh["household_weight"].values

        # Only include valid geoids (positive integers)
        unique_geoids = np.unique(geoids[geoids > 0])

        results: list[dict] = []
        for geoid in unique_geoids:
            mask = geoids == geoid
            w = weights[mask]
            total_weight = float(w.sum())
            if total_weight == 0:
                continue

            b_inc = baseline_income[mask]
            r_inc = reform_income[mask]

            weighted_baseline = float((b_inc * w).sum())
            weighted_reform = float((r_inc * w).sum())

            avg_change = (weighted_reform - weighted_baseline) / total_weight
            rel_change = (
                (weighted_reform / weighted_baseline - 1.0)
                if weighted_baseline != 0
                else 0.0
            )

            geoid_int = int(geoid)
            state_fips = geoid_int // 100
            district_number = geoid_int % 100

            results.append(
                {
                    "district_geoid": geoid_int,
                    "state_fips": state_fips,
                    "district_number": district_number,
                    "average_household_income_change": float(avg_change),
                    "relative_household_income_change": float(rel_change),
                    "population": total_weight,
                }
            )

        self.district_results = results


def compute_us_congressional_district_impacts(
    baseline_simulation: "Simulation",
    reform_simulation: "Simulation",
) -> CongressionalDistrictImpact:
    """Compute per-congressional-district income changes.

    Args:
        baseline_simulation: Completed baseline simulation.
        reform_simulation: Completed reform simulation.

    Returns:
        CongressionalDistrictImpact with district_results populated.
    """
    impact = CongressionalDistrictImpact(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
    )
    impact.run()
    return impact
