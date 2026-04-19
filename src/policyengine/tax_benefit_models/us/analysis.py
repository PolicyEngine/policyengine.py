"""Microsimulation reform analysis for the US model.

The single-household calculator lives in :mod:`.household`; this module
holds the population-level reform-analysis helpers.
"""

from __future__ import annotations

from typing import Union

import pandas as pd
from pydantic import BaseModel

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)
from policyengine.outputs.inequality import (
    Inequality,
    USInequalityPreset,
    calculate_us_inequality,
)
from policyengine.outputs.poverty import (
    Poverty,
    calculate_us_poverty_rates,
)

from .outputs import ProgramStatistics


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    program_statistics: OutputCollection[ProgramStatistics]
    baseline_poverty: OutputCollection[Poverty]
    reform_poverty: OutputCollection[Poverty]
    baseline_inequality: Inequality
    reform_inequality: Inequality


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    inequality_preset: Union[USInequalityPreset, str] = USInequalityPreset.STANDARD,
) -> PolicyReformAnalysis:
    """Perform comprehensive analysis of a US policy reform.

    Args:
        baseline_simulation: Baseline simulation.
        reform_simulation: Reform simulation.
        inequality_preset: Preset for the inequality output.

    Returns:
        ``PolicyReformAnalysis`` with decile impacts, program
        statistics, baseline and reform poverty, and inequality.
    """
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
        income_variable="household_net_income",
    )

    programs = {
        "income_tax": {"entity": "tax_unit", "is_tax": True},
        "payroll_tax": {"entity": "person", "is_tax": True},
        "state_income_tax": {"entity": "tax_unit", "is_tax": True},
        "snap": {"entity": "spm_unit", "is_tax": False},
        "tanf": {"entity": "spm_unit", "is_tax": False},
        "ssi": {"entity": "person", "is_tax": False},
        "social_security": {"entity": "person", "is_tax": False},
        "medicare": {"entity": "person", "is_tax": False},
        "medicaid": {"entity": "person", "is_tax": False},
        "eitc": {"entity": "tax_unit", "is_tax": False},
        "ctc": {"entity": "tax_unit", "is_tax": False},
    }

    program_statistics = []
    for program_name, program_info in programs.items():
        stats = ProgramStatistics(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            program_name=program_name,
            entity=program_info["entity"],
            is_tax=program_info["is_tax"],
        )
        stats.run()
        program_statistics.append(stats)

    program_df = pd.DataFrame(
        [
            {
                "baseline_simulation_id": p.baseline_simulation.id,
                "reform_simulation_id": p.reform_simulation.id,
                "program_name": p.program_name,
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
            for p in program_statistics
        ]
    )
    program_collection = OutputCollection(
        outputs=program_statistics, dataframe=program_df
    )

    baseline_poverty = calculate_us_poverty_rates(baseline_simulation)
    reform_poverty = calculate_us_poverty_rates(reform_simulation)
    baseline_inequality = calculate_us_inequality(
        baseline_simulation, preset=inequality_preset
    )
    reform_inequality = calculate_us_inequality(
        reform_simulation, preset=inequality_preset
    )

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        program_statistics=program_collection,
        baseline_poverty=baseline_poverty,
        reform_poverty=reform_poverty,
        baseline_inequality=baseline_inequality,
        reform_inequality=reform_inequality,
    )
