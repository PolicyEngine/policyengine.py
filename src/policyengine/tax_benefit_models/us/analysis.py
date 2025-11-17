"""General utility functions for US policy reform analysis."""

import pandas as pd
from pydantic import BaseModel

from policyengine.core import OutputCollection, Simulation
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)

from .outputs import ProgramStatistics


class PolicyReformAnalysis(BaseModel):
    """Complete policy reform analysis result."""

    decile_impacts: OutputCollection[DecileImpact]
    program_statistics: OutputCollection[ProgramStatistics]


def general_policy_reform_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> PolicyReformAnalysis:
    """Perform comprehensive analysis of a policy reform.

    Returns:
        PolicyReformAnalysis containing decile impacts and program statistics
    """
    # Decile impact (using household_net_income for US)
    decile_impacts = calculate_decile_impacts(
        baseline_simulation=baseline_simulation,
        reform_simulation=reform_simulation,
        income_variable="household_net_income",
    )

    # Major programs to analyse
    programs = {
        # Federal taxes
        "income_tax": {"entity": "tax_unit", "is_tax": True},
        "payroll_tax": {"entity": "person", "is_tax": True},
        # State and local taxes
        "state_income_tax": {"entity": "tax_unit", "is_tax": True},
        # Benefits
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
        entity = program_info["entity"]
        is_tax = program_info["is_tax"]

        stats = ProgramStatistics(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            program_name=program_name,
            entity=entity,
            is_tax=is_tax,
        )
        stats.run()
        program_statistics.append(stats)

    # Create DataFrame
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

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts, program_statistics=program_collection
    )
