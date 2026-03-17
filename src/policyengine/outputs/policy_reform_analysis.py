"""Unified result container for a complete policy reform analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from policyengine.core import OutputCollection
from policyengine.outputs.decile_impact import DecileImpact
from policyengine.outputs.inequality import Inequality
from policyengine.outputs.intra_decile_impact import IntraDecileImpact
from policyengine.outputs.poverty import Poverty

if TYPE_CHECKING:
    from policyengine.outputs.budget_summary import BudgetSummaryItem


class PolicyReformAnalysis(BaseModel):
    """Complete result of an economic impact analysis.

    This is a pure result container — it does no computation itself.
    ``economic_impact_analysis()`` (in each country's ``analysis.py``)
    builds and returns an instance of this class.

    Geographic outputs (constituency, local authority, congressional
    district) and wealth deciles are **not** included here because
    they depend on external data or optional dataset variables and
    must be able to fail independently of the core analysis.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Distributional
    decile_impacts: OutputCollection[DecileImpact]
    intra_decile_impacts: OutputCollection[IntraDecileImpact]

    # Budget
    budget_summary: OutputCollection[BudgetSummaryItem]
    household_count_baseline: float
    household_count_reform: float

    # Programs
    program_statistics: (
        OutputCollection  # US ProgramStatistics or UK ProgrammeStatistics
    )

    # Poverty — overall always present, demographics optional
    baseline_poverty: OutputCollection[Poverty]
    reform_poverty: OutputCollection[Poverty]
    baseline_poverty_by_age: OutputCollection[Poverty] | None = None
    reform_poverty_by_age: OutputCollection[Poverty] | None = None
    baseline_poverty_by_gender: OutputCollection[Poverty] | None = None
    reform_poverty_by_gender: OutputCollection[Poverty] | None = None
    baseline_poverty_by_race: OutputCollection[Poverty] | None = None
    reform_poverty_by_race: OutputCollection[Poverty] | None = None

    # Inequality
    baseline_inequality: Inequality
    reform_inequality: Inequality
