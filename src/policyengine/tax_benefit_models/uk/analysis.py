"""Microsimulation reform analysis for the UK model.

The single-household calculator lives in :mod:`.household`; this module
holds the population-level reform-analysis helpers.
"""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)
from policyengine.outputs.inequality import (
    Inequality,
    calculate_uk_inequality,
)
from policyengine.outputs.poverty import (
    Poverty,
    calculate_uk_poverty_rates,
)

from .outputs import ProgrammeStatistics


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    programme_statistics: OutputCollection[ProgrammeStatistics]
    baseline_poverty: OutputCollection[Poverty]
    reform_poverty: OutputCollection[Poverty]
    baseline_inequality: Inequality
    reform_inequality: Inequality


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive analysis of a UK policy reform."""
    baseline_simulation.ensure()
    reform_simulation.ensure()

    assert len(baseline_simulation.dataset.data.household) > 100, (
        "Baseline simulation must have more than 100 households"
    )
    assert len(reform_simulation.dataset.data.household) > 100, (
        "Reform simulation must have more than 100 households"
    )

    decile_impacts = calculate_decile_impacts(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
    )

    programmes = {
        "income_tax": {"is_tax": True},
        "national_insurance": {"is_tax": True},
        "vat": {"is_tax": True},
        "council_tax": {"is_tax": True},
        "universal_credit": {"is_tax": False},
        "child_benefit": {"is_tax": False},
        "pension_credit": {"is_tax": False},
        "income_support": {"is_tax": False},
        "working_tax_credit": {"is_tax": False},
        "child_tax_credit": {"is_tax": False},
    }

    programme_statistics = []
    for programme_name, programme_info in programmes.items():
        entity = baseline_simulation.tax_benefit_model_version.get_variable(
            programme_name
        ).entity
        stats = ProgrammeStatistics(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            programme_name=programme_name,
            entity=entity,
            is_tax=programme_info["is_tax"],
        )
        stats.run()
        programme_statistics.append(stats)

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

    baseline_poverty = calculate_uk_poverty_rates(baseline_simulation)
    reform_poverty = calculate_uk_poverty_rates(reform_simulation)
    baseline_inequality = calculate_uk_inequality(baseline_simulation)
    reform_inequality = calculate_uk_inequality(reform_simulation)

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        programme_statistics=programme_collection,
        baseline_poverty=baseline_poverty,
        reform_poverty=reform_poverty,
        baseline_inequality=baseline_inequality,
        reform_inequality=reform_inequality,
    )
