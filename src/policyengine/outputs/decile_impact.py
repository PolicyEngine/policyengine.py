import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output, OutputCollection, Simulation


class DecileImpact(Output):
    """Single decile's impact from a policy reform - represents one database row."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: Simulation
    reform_simulation: Simulation
    income_variable: str = "equiv_hbai_household_net_income"
    entity: str | None = None
    decile: int
    quantiles: int = 10

    # Results populated by run()
    baseline_mean: float | None = None
    reform_mean: float | None = None
    absolute_change: float | None = None
    relative_change: float | None = None
    count_better_off: float | None = None
    count_worse_off: float | None = None
    count_no_change: float | None = None

    def run(self):
        """Calculate impact for this specific decile."""
        # Get variable object to determine entity
        var_obj = next(
            v
            for v in self.baseline_simulation.tax_benefit_model_version.variables
            if v.name == self.income_variable
        )

        # Get target entity
        target_entity = self.entity or var_obj.entity

        # Get data from both simulations
        baseline_data = getattr(
            self.baseline_simulation.output_dataset.data, target_entity
        )
        reform_data = getattr(
            self.reform_simulation.output_dataset.data, target_entity
        )

        # Map income variable to target entity if needed
        if var_obj.entity != target_entity:
            baseline_mapped = (
                self.baseline_simulation.output_dataset.data.map_to_entity(
                    var_obj.entity, target_entity
                )
            )
            baseline_income = baseline_mapped[self.income_variable]

            reform_mapped = (
                self.reform_simulation.output_dataset.data.map_to_entity(
                    var_obj.entity, target_entity
                )
            )
            reform_income = reform_mapped[self.income_variable]
        else:
            baseline_income = baseline_data[self.income_variable]
            reform_income = reform_data[self.income_variable]

        # Calculate deciles based on baseline income
        decile_series = (
            pd.qcut(
                baseline_income,
                self.quantiles,
                labels=False,
                duplicates="drop",
            )
            + 1
        )

        # Calculate changes
        absolute_change = reform_income - baseline_income
        relative_change = (absolute_change / baseline_income) * 100

        # Filter to this decile
        mask = decile_series == self.decile

        # Populate results
        self.baseline_mean = float(baseline_income[mask].mean())
        self.reform_mean = float(reform_income[mask].mean())
        self.absolute_change = float(absolute_change[mask].mean())
        self.relative_change = float(relative_change[mask].mean())
        self.count_better_off = float((absolute_change[mask] > 0).sum())
        self.count_worse_off = float((absolute_change[mask] < 0).sum())
        self.count_no_change = float((absolute_change[mask] == 0).sum())


def calculate_decile_impacts(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    income_variable: str = "equiv_hbai_household_net_income",
    entity: str | None = None,
    quantiles: int = 10,
) -> OutputCollection[DecileImpact]:
    """Calculate decile-by-decile impact of a reform.

    Returns:
        OutputCollection containing list of DecileImpact objects and DataFrame
    """
    results = []
    for decile in range(1, quantiles + 1):
        impact = DecileImpact(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            income_variable=income_variable,
            entity=entity,
            decile=decile,
            quantiles=quantiles,
        )
        impact.run()
        results.append(impact)

    # Create DataFrame
    df = pd.DataFrame(
        [
            {
                "baseline_simulation_id": r.baseline_simulation.id,
                "reform_simulation_id": r.reform_simulation.id,
                "income_variable": r.income_variable,
                "decile": r.decile,
                "baseline_mean": r.baseline_mean,
                "reform_mean": r.reform_mean,
                "absolute_change": r.absolute_change,
                "relative_change": r.relative_change,
                "count_better_off": r.count_better_off,
                "count_worse_off": r.count_worse_off,
                "count_no_change": r.count_no_change,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)
