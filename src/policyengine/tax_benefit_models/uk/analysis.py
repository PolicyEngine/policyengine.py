"""General utility functions for UK policy reform analysis."""

import pandas as pd
from pydantic import BaseModel

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)

from .outputs import ProgrammeStatistics


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    programme_statistics: OutputCollection[ProgrammeStatistics]


def general_policy_reform_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive analysis of a policy reform.

    Returns:
        PolicyReformAnalysis containing decile impacts and programme statistics
    """
    # Decile impact
    decile_impacts = calculate_decile_impacts(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
    )

    # Major programmes to analyse
    programmes = {
        # Tax
        "income_tax": {"entity": "person", "is_tax": True},
        "national_insurance": {"entity": "person", "is_tax": True},
        "vat": {"entity": "household", "is_tax": True},
        "council_tax": {"entity": "household", "is_tax": True},
        # Benefits
        "universal_credit": {"entity": "person", "is_tax": False},
        "child_benefit": {"entity": "person", "is_tax": False},
        "pension_credit": {"entity": "person", "is_tax": False},
        "income_support": {"entity": "person", "is_tax": False},
        "working_tax_credit": {"entity": "person", "is_tax": False},
        "child_tax_credit": {"entity": "person", "is_tax": False},
    }

    programme_statistics = []

    for programme_name, programme_info in programmes.items():
        entity = programme_info["entity"]
        is_tax = programme_info["is_tax"]

        stats = ProgrammeStatistics(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            programme_name=programme_name,
            entity=entity,
            is_tax=is_tax,
        )
        stats.run()
        programme_statistics.append(stats)

    # Create DataFrame
    programme_df = pd.DataFrame(
        [
            {
                "baseline_simulation_id": p.baseline_simulation.id,
                "reform_simulation_id": p.reform_simulation.id,
                "programme_name": p.programme_name,
                "entity": p.entity,
                "is_tax": p.is_tax,
                "baseline_total": p.baseline_total,
                "reform_total": p.reform_total,
                "change": p.change,
                "baseline_count": p.baseline_count,
                "reform_count": p.reform_count,
                "winners": p.winners,
                "losers": p.losers,
            }
            for p in programme_statistics
        ]
    )

    programme_collection = OutputCollection(
        outputs=programme_statistics, dataframe=programme_df
    )

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        programme_statistics=programme_collection,
    )
