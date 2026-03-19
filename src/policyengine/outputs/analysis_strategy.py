"""Strategy protocol and result types for economic impact analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypedDict, runtime_checkable

from pydantic import BaseModel, ConfigDict

from policyengine.core import OutputCollection
from policyengine.outputs.inequality import Inequality
from policyengine.outputs.poverty import Poverty

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation


class ProgramDefinition(TypedDict):
    """Definition of a program for program statistics computation."""

    entity: str
    is_tax: bool


class PovertyResult(BaseModel):
    """Standardised poverty result returned by a country strategy."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_poverty: OutputCollection[Poverty]
    reform_poverty: OutputCollection[Poverty]
    baseline_poverty_by_age: OutputCollection[Poverty] | None = None
    reform_poverty_by_age: OutputCollection[Poverty] | None = None
    baseline_poverty_by_gender: OutputCollection[Poverty] | None = None
    reform_poverty_by_gender: OutputCollection[Poverty] | None = None
    baseline_poverty_by_race: OutputCollection[Poverty] | None = None
    reform_poverty_by_race: OutputCollection[Poverty] | None = None


class InequalityResult(BaseModel):
    """Standardised inequality result returned by a country strategy."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_inequality: Inequality
    reform_inequality: Inequality


@runtime_checkable
class AnalysisStrategy(Protocol):
    """Country-specific strategy for economic impact analysis.

    Each property/method corresponds to a standardised extension point
    in the shared analysis pipeline.
    """

    @property
    def income_variable(self) -> str:
        """Primary income variable for decile / intra-decile analysis."""
        ...

    @property
    def budget_variable_names(self) -> list[str]:
        """Variable names for budget summary.

        Entities are looked up from the tax-benefit system at runtime.
        """
        ...

    @property
    def programs(self) -> dict[str, ProgramDefinition]:
        """Program definitions: name -> ProgramDefinition."""
        ...

    def compute_poverty(
        self,
        baseline: Simulation,
        reform: Simulation,
    ) -> PovertyResult:
        """Compute all poverty metrics (overall + demographic breakdowns)."""
        ...

    def compute_inequality(
        self,
        baseline: Simulation,
        reform: Simulation,
    ) -> InequalityResult:
        """Compute inequality metrics."""
        ...
