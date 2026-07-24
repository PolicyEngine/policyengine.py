"""Shared preparation for decile-based baseline-reform analysis."""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from policyengine.core import Simulation
from policyengine.outputs.decile_grouping import (
    _get_analysis_weight,
    _get_decile_weights,
    calculate_decile_groups,
)


@dataclass(frozen=True)
class _PreparedDecileAnalysis:
    """Validated arrays and masks shared by decile impact outputs."""

    entity: str
    quantiles: int
    index: pd.Index
    baseline_income: np.ndarray
    reform_income: np.ndarray
    groups: pd.Series
    analysis_weight: np.ndarray
    effective_weight: np.ndarray
    included: np.ndarray


def _variable_entity(
    simulation: Simulation,
    variable_name: str,
) -> Optional[str]:
    """Return a variable's entity when model metadata is available."""
    variables = getattr(
        simulation.tax_benefit_model_version,
        "variables",
        (),
    )
    try:
        variable = next(
            variable for variable in variables if variable.name == variable_name
        )
    except (StopIteration, TypeError):
        return None
    return str(variable.entity)


def _income_at_entity(
    simulation: Simulation,
    *,
    income_variable: str,
    variable_entity: Optional[str],
    target_entity: str,
):
    """Read or map an income variable onto the target analysis entity."""
    output_dataset = simulation.output_dataset
    if output_dataset is None:
        raise ValueError("Simulation output dataset is not available")
    data = output_dataset.data
    if data is None:
        raise ValueError("Simulation output data is not available")
    if variable_entity is not None and variable_entity != target_entity:
        mapped = data.map_to_entity(variable_entity, target_entity)
        return mapped[income_variable]
    return getattr(data, target_entity)[income_variable]


def _prepare_decile_analysis(
    baseline_simulation: Simulation,
    reform_simulation: Simulation,
    *,
    income_variable: str,
    decile_variable: Optional[str],
    entity: Optional[str],
    quantiles: int,
    require_effective_weight: bool = False,
) -> _PreparedDecileAnalysis:
    """Validate and prepare inputs used by both decile impact outputs."""
    if quantiles < 1:
        raise ValueError("quantiles must be at least 1")

    variable_entity = _variable_entity(
        baseline_simulation,
        income_variable,
    )
    target_entity = entity or variable_entity
    if target_entity is None:
        raise ValueError(
            f"Could not determine the entity for income variable '{income_variable}'"
        )

    baseline_output = baseline_simulation.output_dataset
    reform_output = reform_simulation.output_dataset
    if baseline_output is None or baseline_output.data is None:
        raise ValueError("Baseline simulation output data is not available")
    if reform_output is None or reform_output.data is None:
        raise ValueError("Reform simulation output data is not available")
    baseline_data = getattr(baseline_output.data, target_entity)
    reform_data = getattr(reform_output.data, target_entity)
    if not baseline_data.index.equals(reform_data.index):
        raise ValueError(
            "Baseline and reform simulation observations must have identical indexes"
        )

    baseline_income_series = _income_at_entity(
        baseline_simulation,
        income_variable=income_variable,
        variable_entity=variable_entity,
        target_entity=target_entity,
    )
    reform_income_series = _income_at_entity(
        reform_simulation,
        income_variable=income_variable,
        variable_entity=variable_entity,
        target_entity=target_entity,
    )
    if not baseline_income_series.index.equals(baseline_data.index):
        raise ValueError("Baseline income values must align with baseline observations")
    if not reform_income_series.index.equals(reform_data.index):
        raise ValueError("Reform income values must align with reform observations")

    baseline_income = np.asarray(baseline_income_series, dtype=float)
    reform_income = np.asarray(reform_income_series, dtype=float)
    analysis_weight = _get_analysis_weight(
        baseline_data,
        entity=target_entity,
    )
    if require_effective_weight or decile_variable is None:
        _, effective_weight = _get_decile_weights(
            baseline_data,
            entity=target_entity,
        )
    else:
        # A precomputed group plus a household-weighted output does not need
        # household size. Keep the prepared shape uniform without imposing an
        # unrelated input requirement.
        effective_weight = analysis_weight.copy()
    groups = calculate_decile_groups(
        baseline_data,
        baseline_income_series,
        decile_variable=decile_variable,
        entity=target_entity,
        quantiles=quantiles,
    )
    included = groups.isin(range(1, quantiles + 1)).to_numpy(dtype=bool)

    if not np.all(np.isfinite(baseline_income[included])):
        raise ValueError(
            "Included observations must have finite baseline income values"
        )
    if not np.all(np.isfinite(reform_income[included])):
        raise ValueError("Included observations must have finite reform income values")

    return _PreparedDecileAnalysis(
        entity=target_entity,
        quantiles=quantiles,
        index=baseline_data.index,
        baseline_income=baseline_income,
        reform_income=reform_income,
        groups=groups,
        analysis_weight=analysis_weight,
        effective_weight=effective_weight,
        included=included,
    )


def _weighted_mean(
    values: np.ndarray,
    weights: np.ndarray,
) -> Optional[float]:
    """Return a weighted mean, or ``None`` without positive total weight."""
    total_weight = float(np.sum(weights))
    if total_weight == 0:
        return None
    return float(np.sum(values * weights) / total_weight)
