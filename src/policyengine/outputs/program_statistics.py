"""Shared `ProgramStatistics` for reform-impact tables (US + UK)."""

from typing import Optional

import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output, OutputCollection, Simulation
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType,
)
from policyengine.utils.errors import format_conditional_error_detail


class ProgramStatistics(Output):
    """Single program's statistics from a policy reform.

    Count fields are reported in the configured entity's units. For example,
    a tax-unit variable reports tax-unit recipient/winner/loser counts, while
    a person variable reports person counts.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    baseline_simulation: Simulation
    reform_simulation: Simulation
    program_name: str
    entity: str
    is_tax: bool = False

    # Results populated by run()
    baseline_total: Optional[float] = None
    reform_total: Optional[float] = None
    change: Optional[float] = None
    baseline_count: Optional[float] = None
    reform_count: Optional[float] = None
    winners: Optional[float] = None
    losers: Optional[float] = None

    def run(self):
        """Calculate statistics for this program."""
        # Baseline totals
        baseline_total = Aggregate(
            simulation=self.baseline_simulation,
            variable=self.program_name,
            aggregate_type=AggregateType.SUM,
            entity=self.entity,
        )
        baseline_total.run()

        # Reform totals
        reform_total = Aggregate(
            simulation=self.reform_simulation,
            variable=self.program_name,
            aggregate_type=AggregateType.SUM,
            entity=self.entity,
        )
        reform_total.run()

        # Count of recipients/payers (baseline)
        baseline_count = Aggregate(
            simulation=self.baseline_simulation,
            variable=self.program_name,
            aggregate_type=AggregateType.COUNT,
            entity=self.entity,
            filter_variable=self.program_name,
            filter_variable_geq=0.01,
        )
        baseline_count.run()

        # Count of recipients/payers (reform)
        reform_count = Aggregate(
            simulation=self.reform_simulation,
            variable=self.program_name,
            aggregate_type=AggregateType.COUNT,
            entity=self.entity,
            filter_variable=self.program_name,
            filter_variable_geq=0.01,
        )
        reform_count.run()

        # Winners and losers
        winners = ChangeAggregate(
            baseline_simulation=self.baseline_simulation,
            reform_simulation=self.reform_simulation,
            variable=self.program_name,
            aggregate_type=ChangeAggregateType.COUNT,
            entity=self.entity,
            change_geq=0.01 if not self.is_tax else -0.01,
        )
        winners.run()

        losers = ChangeAggregate(
            baseline_simulation=self.baseline_simulation,
            reform_simulation=self.reform_simulation,
            variable=self.program_name,
            aggregate_type=ChangeAggregateType.COUNT,
            entity=self.entity,
            change_leq=-0.01 if not self.is_tax else 0.01,
        )
        losers.run()

        # Populate results
        self.baseline_total = float(baseline_total.result)
        self.reform_total = float(reform_total.result)
        self.change = float(reform_total.result - baseline_total.result)
        self.baseline_count = float(baseline_count.result)
        self.reform_count = float(reform_count.result)
        self.winners = float(winners.result)
        self.losers = float(losers.result)


def _format_missing_program_variables(missing_variables: set[str]) -> Optional[str]:
    """Format the optional missing-variable detail for program statistics."""
    return format_conditional_error_detail(
        "Missing model variables",
        missing_variables,
    )


def _program_statistics_config_error_message(
    country_label: str,
    missing_variables: set[str],
    missing_outputs: set[tuple[str, str]],
) -> str:
    lines = [f"{country_label} program statistics config is invalid:"]

    missing_variables_message = _format_missing_program_variables(missing_variables)
    if missing_variables_message is not None:
        lines.append(missing_variables_message)

    if missing_outputs:
        formatted = ", ".join(
            f"{program_name} on {entity}"
            for program_name, entity in sorted(missing_outputs)
        )
        lines.append("Variables not materialized in simulation outputs: " + formatted)
        lines.append(
            "Add them to the model version's entity_variables or pass them "
            "via Simulation.extra_variables before running the simulation."
        )

    return "\n".join(lines)


def validate_program_statistics_config(
    programs: dict[str, dict],
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    country_label: str,
) -> None:
    """Validate program-statistics variables before running simulations.

    ``programs`` maps each program-statistics variable name to its metadata.
    ``country_label`` (for example ``"US"`` or ``"UK"``) only shapes the error
    message; the validation logic itself is country-agnostic. Raises
    ``ValueError`` if any program variable is missing from the model or is not
    materialized in the simulation outputs.
    """
    missing_variables: set[str] = set()
    missing_outputs: set[tuple[str, str]] = set()

    simulations = (baseline_simulation, reform_simulation)
    for program_name in programs:
        for simulation in simulations:
            model_version = simulation.tax_benefit_model_version
            try:
                variable = model_version.get_variable(program_name)
            except ValueError:
                missing_variables.add(program_name)
                continue

            resolved_variables = model_version.resolve_entity_variables(simulation)
            if program_name not in resolved_variables.get(variable.entity, []):
                missing_outputs.add((program_name, variable.entity))

    if not missing_variables and not missing_outputs:
        return

    raise ValueError(
        _program_statistics_config_error_message(
            country_label,
            missing_variables,
            missing_outputs,
        ),
    )


def build_program_statistics(
    programs: dict[str, dict],
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
) -> OutputCollection[ProgramStatistics]:
    """Run program statistics for each configured program.

    ``programs`` maps each program-statistics variable name to its metadata
    (currently just ``is_tax``). Each program's entity is derived from the
    model's variable metadata, so the set of programs cannot silently drift when
    a country package moves a variable between entities. Returns the collection
    of ``ProgramStatistics`` with an assembled dataframe of per-program totals,
    counts, winners, and losers.
    """
    model_version = baseline_simulation.tax_benefit_model_version
    program_statistics = []
    for program_name, program_info in programs.items():
        stats = ProgramStatistics(
            baseline_simulation=baseline_simulation,
            reform_simulation=reform_simulation,
            program_name=program_name,
            entity=model_version.get_variable(program_name).entity,
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
    return OutputCollection(outputs=program_statistics, dataframe=program_df)
