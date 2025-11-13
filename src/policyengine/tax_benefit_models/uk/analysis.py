"""General utility functions for UK policy reform analysis."""

from policyengine.core import Simulation
from policyengine.outputs.decile_impact import DecileImpact, calculate_decile_impacts
from .outputs import ProgrammeStatistics
import pandas as pd


def general_policy_reform_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> tuple[list[DecileImpact], list[ProgrammeStatistics], pd.DataFrame, pd.DataFrame]:
    """Perform comprehensive analysis of a policy reform.

    Returns:
        tuple of:
        - list[DecileImpact]: Decile-by-decile impacts
        - list[ProgrammeStatistics]: Statistics for major programmes
        - pd.DataFrame: Decile impacts as DataFrame
        - pd.DataFrame: Programme statistics as DataFrame
    """
    # Decile impact
    decile_impacts, decile_df = calculate_decile_impacts(
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

    # Create DataFrames for convenience
    programme_df = pd.DataFrame([
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
    ])

    return decile_impacts, programme_statistics, decile_df, programme_df
