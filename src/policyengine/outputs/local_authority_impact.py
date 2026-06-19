"""UK local authority impact output class.

Computes per-local-authority income changes by grouping household output rows
on longwise geography codes carried by the dataset.
"""

from typing import TYPE_CHECKING, Optional, Sequence

import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output
from policyengine.data.uk_geography_assets import LOCAL_AUTHORITY_ASSET_SPEC
from policyengine.outputs.uk_geography_assets import (
    UKGeographyAssetStrategy,
)
from policyengine.outputs.uk_geography_impact import (
    compute_longwise_uk_geography_impacts,
    resolve_uk_geography_lookup_csv_path,
)

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class LocalAuthorityImpact(Output):
    """Per-local-authority income change from a UK policy reform.

    Groups households by ``la_code_oa`` and computes weighted average and
    relative household income changes.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    weight_matrix_path: Optional[str] = None
    local_authority_csv_path: Optional[str] = None
    year: str = "2025"

    # Results populated by run()
    local_authority_results: Optional[list[dict]] = None

    def run(self) -> None:
        """Group household output rows and compute per-local-authority metrics."""
        baseline_hh = self.baseline_simulation.output_dataset.data.household
        reform_hh = self.reform_simulation.output_dataset.data.household

        self.local_authority_results = compute_longwise_uk_geography_impacts(
            baseline_household=pd.DataFrame(baseline_hh),
            reform_household=pd.DataFrame(reform_hh),
            geography_column="la_code_oa",
            result_key_prefix="local_authority",
            lookup_csv_path=self.local_authority_csv_path,
        )


def compute_uk_local_authority_impacts(
    baseline_simulation: "Simulation",
    reform_simulation: "Simulation",
    weight_matrix_path: Optional[str] = None,
    local_authority_csv_path: Optional[str] = None,
    year: str = "2025",
    asset_strategies: Optional[Sequence[UKGeographyAssetStrategy]] = None,
    download_missing_assets: bool = True,
) -> LocalAuthorityImpact:
    """Compute per-local-authority income changes for UK.

    Args:
        baseline_simulation: Completed baseline simulation.
        reform_simulation: Completed reform simulation.
        weight_matrix_path: Deprecated and ignored. Local-authority outputs
            now group by ``la_code_oa`` on the household output.
        local_authority_csv_path: Optional path to local_authorities_2021.csv.
            If omitted, standard local paths are checked before downloading
            from GCS. If still unavailable, results use geography codes as names.
        year: Deprecated and ignored.
        asset_strategies: Deprecated and ignored.
        download_missing_assets: Whether to download the optional lookup CSV
            from GCS when no local CSV is found.

    Returns:
        LocalAuthorityImpact with local_authority_results populated.
    """
    lookup_csv_path = resolve_uk_geography_lookup_csv_path(
        LOCAL_AUTHORITY_ASSET_SPEC,
        lookup_csv_path=local_authority_csv_path,
        download_missing_assets=download_missing_assets,
    )
    impact = LocalAuthorityImpact.model_construct(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        weight_matrix_path=weight_matrix_path,
        local_authority_csv_path=lookup_csv_path,
        year=year,
    )
    impact.run()
    return impact
