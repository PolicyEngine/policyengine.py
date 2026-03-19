"""Shared cross-country economic impact analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from policyengine.outputs.analysis_strategy import AnalysisStrategy
from policyengine.outputs.budget_summary import compute_budget_summary
from policyengine.outputs.decile_impact import compute_decile_impacts
from policyengine.outputs.intra_decile_impact import compute_intra_decile_impacts
from policyengine.outputs.policy_reform_analysis import PolicyReformAnalysis
from policyengine.outputs.program_statistics import compute_program_statistics

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


def economic_impact_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    strategy: AnalysisStrategy,
) -> PolicyReformAnalysis:
    """Perform comprehensive economic impact analysis of a policy reform.

    Shared implementation that delegates country-specific work to
    *strategy* at five standardised extension points.

    Both simulations must already be run (i.e. ``ensure()`` called).
    """
    if not isinstance(strategy, AnalysisStrategy):
        raise TypeError(
            f"strategy must implement the AnalysisStrategy protocol, "
            f"but got {type(strategy).__name__}. Ensure it defines: "
            f"income_variable, budget_variable_names, programs, "
            f"compute_poverty(), and compute_inequality()."
        )

    baseline_simulation.ensure()
    reform_simulation.ensure()

    # --- shared computations ------------------------------------------------

    # Decile impacts
    decile_impacts = compute_decile_impacts(
        baseline_simulation,
        reform_simulation,
        income_variable=strategy.income_variable,
    )

    # Intra-decile impacts
    intra_decile_impacts = compute_intra_decile_impacts(
        baseline_simulation,
        reform_simulation,
        income_variable=strategy.income_variable,
    )

    # Budget summary (entity looked up from TBM inside compute_budget_summary)
    budget = compute_budget_summary(
        baseline_simulation,
        reform_simulation,
        strategy.budget_variable_names,
    )

    # Household counts — raw weight sums to avoid MicroSeries double-weighting
    hh_weight_baseline = baseline_simulation.output_dataset.data.household[
        "household_weight"
    ]
    hh_weight_reform = reform_simulation.output_dataset.data.household[
        "household_weight"
    ]
    household_count_baseline = float(np.array(hh_weight_baseline).sum())
    household_count_reform = float(np.array(hh_weight_reform).sum())

    # Program statistics
    programs = compute_program_statistics(
        baseline_simulation,
        reform_simulation,
        strategy.programs,
    )

    # --- strategy extension points ------------------------------------------

    poverty = strategy.compute_poverty(baseline_simulation, reform_simulation)
    inequality = strategy.compute_inequality(baseline_simulation, reform_simulation)

    # --- assemble result ----------------------------------------------------

    return PolicyReformAnalysis(
        decile_impacts=decile_impacts,
        intra_decile_impacts=intra_decile_impacts,
        budget_summary=budget,
        household_count_baseline=household_count_baseline,
        household_count_reform=household_count_reform,
        program_statistics=programs,
        baseline_poverty=poverty.baseline_poverty,
        reform_poverty=poverty.reform_poverty,
        baseline_poverty_by_age=poverty.baseline_poverty_by_age,
        reform_poverty_by_age=poverty.reform_poverty_by_age,
        baseline_poverty_by_gender=poverty.baseline_poverty_by_gender,
        reform_poverty_by_gender=poverty.reform_poverty_by_gender,
        baseline_poverty_by_race=poverty.baseline_poverty_by_race,
        reform_poverty_by_race=poverty.reform_poverty_by_race,
        baseline_inequality=inequality.baseline_inequality,
        reform_inequality=inequality.reform_inequality,
    )
