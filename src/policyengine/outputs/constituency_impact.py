"""UK parliamentary constituency impact output class.

Computes per-constituency income changes by grouping household output rows
on longwise geography codes carried by the dataset.
"""

from typing import TYPE_CHECKING, Optional, Sequence

import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output
from policyengine.data.uk_geography_assets import CONSTITUENCY_ASSET_SPEC
from policyengine.outputs.uk_geography_assets import (
    UKGeographyAssetStrategy,
)
from policyengine.outputs.uk_geography_impact import (
    compute_longwise_uk_geography_impacts,
    resolve_uk_geography_lookup_csv_path,
)

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class ConstituencyImpact(Output):
    """Per-parliamentary-constituency income change from a UK policy reform.

    Groups households by ``constituency_code_oa`` and computes weighted
    average and relative household income changes.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    weight_matrix_path: Optional[str] = None
    constituency_csv_path: Optional[str] = None
    year: str = "2025"

    # Results populated by run()
    constituency_results: Optional[list[dict]] = None

    def run(self) -> None:
        """Group household output rows and compute per-constituency metrics."""
        baseline_hh = self.baseline_simulation.output_dataset.data.household
        reform_hh = self.reform_simulation.output_dataset.data.household

        self.constituency_results = compute_longwise_uk_geography_impacts(
            baseline_household=pd.DataFrame(baseline_hh),
            reform_household=pd.DataFrame(reform_hh),
            geography_column="constituency_code_oa",
            result_key_prefix="constituency",
            lookup_csv_path=self.constituency_csv_path,
        )


def compute_uk_constituency_impacts(
    baseline_simulation: "Simulation",
    reform_simulation: "Simulation",
    weight_matrix_path: Optional[str] = None,
    constituency_csv_path: Optional[str] = None,
    year: str = "2025",
    asset_strategies: Optional[Sequence[UKGeographyAssetStrategy]] = None,
    download_missing_assets: bool = True,
) -> ConstituencyImpact:
    """Compute per-constituency income changes for UK.

    Args:
        baseline_simulation: Completed baseline simulation.
        reform_simulation: Completed reform simulation.
        weight_matrix_path: Deprecated and ignored. Constituency outputs now
            group by ``constituency_code_oa`` on the household output.
        constituency_csv_path: Optional path to constituencies_2024.csv.
            If omitted, standard local paths are checked before downloading
            from GCS. If still unavailable, results use geography codes as names.
        year: Deprecated and ignored.
        asset_strategies: Deprecated and ignored.
        download_missing_assets: Whether to download the optional lookup CSV
            from GCS when no local CSV is found.

    Returns:
        ConstituencyImpact with constituency_results populated.
    """
    lookup_csv_path = resolve_uk_geography_lookup_csv_path(
        CONSTITUENCY_ASSET_SPEC,
        lookup_csv_path=constituency_csv_path,
        download_missing_assets=download_missing_assets,
    )
    impact = ConstituencyImpact.model_construct(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        weight_matrix_path=weight_matrix_path,
        constituency_csv_path=lookup_csv_path,
        year=year,
    )
    impact.run()
    return impact
