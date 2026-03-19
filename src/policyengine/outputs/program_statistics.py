"""Shared compute function for program/programme statistics."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from policyengine.core import OutputCollection
from policyengine.outputs.analysis_strategy import ProgramDefinition

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation

logger = logging.getLogger(__name__)


def compute_program_statistics(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    programs: dict[str, ProgramDefinition],
) -> OutputCollection:
    """Compute per-program statistics for a policy reform.

    Args:
        baseline_simulation: Already-run baseline simulation.
        reform_simulation: Already-run reform simulation.
        programs: Mapping of program name to :class:`ProgramDefinition`
            with keys ``"entity"`` (str) and ``"is_tax"`` (bool).
            Example::

                {
                    "income_tax": {"entity": "tax_unit", "is_tax": True},
                    "snap": {"entity": "spm_unit", "is_tax": False},
                }

    Returns:
        OutputCollection of ProgramStatistics/ProgrammeStatistics objects.
        Programs that raise KeyError or ValueError are silently skipped.
    """
    # Import both variants — only one will actually be used depending on
    # which country package is installed, but we try both so this function
    # works for either.
    ProgramStats: type | None = None
    try:
        from policyengine.tax_benefit_models.us.outputs import ProgramStatistics

        ProgramStats = ProgramStatistics
    except ImportError:
        pass
    if ProgramStats is None:
        try:
            from policyengine.tax_benefit_models.uk.outputs import ProgrammeStatistics

            ProgramStats = ProgrammeStatistics
        except ImportError:
            pass
    if ProgramStats is None:
        raise ImportError(
            "Neither ProgramStatistics (US) nor ProgrammeStatistics (UK) could be imported"
        )

    # Determine the field name for the program name attribute
    # US uses "program_name", UK uses "programme_name"
    if hasattr(ProgramStats, "model_fields"):
        name_field = (
            "program_name"
            if "program_name" in ProgramStats.model_fields
            else "programme_name"
        )
    else:
        name_field = "program_name"

    results = []
    for prog_name, prog_info in programs.items():
        try:
            stats = ProgramStats(
                baseline_simulation=baseline_simulation,
                reform_simulation=reform_simulation,
                **{name_field: prog_name},
                entity=prog_info["entity"],
                is_tax=prog_info.get("is_tax", False),
            )
            stats.run()
            results.append(stats)
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping program %s: %s", prog_name, exc, exc_info=True)
            continue

    df = pd.DataFrame(
        [
            {
                "program_name": getattr(r, name_field),
                "entity": r.entity,
                "is_tax": r.is_tax,
                "baseline_total": r.baseline_total,
                "reform_total": r.reform_total,
                "change": r.change,
                "baseline_count": r.baseline_count,
                "reform_count": r.reform_count,
                "winners": r.winners,
                "losers": r.losers,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)
