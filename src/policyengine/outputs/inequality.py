"""Inequality analysis output types."""

from typing import Any

import numpy as np
import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output, Simulation


def _gini(values: np.ndarray, weights: np.ndarray) -> float:
    """Calculate weighted Gini coefficient.

    Args:
        values: Array of income values
        weights: Array of weights

    Returns:
        Gini coefficient between 0 (perfect equality) and 1 (perfect inequality)
    """
    # Handle edge cases
    if len(values) == 0 or weights.sum() == 0:
        return 0.0

    # Sort by values
    sorted_indices = np.argsort(values)
    sorted_values = values[sorted_indices]
    sorted_weights = weights[sorted_indices]

    # Cumulative weights and weighted values
    cumulative_weights = np.cumsum(sorted_weights)
    total_weight = cumulative_weights[-1]
    cumulative_weighted_values = np.cumsum(sorted_values * sorted_weights)
    total_weighted_value = cumulative_weighted_values[-1]

    if total_weighted_value == 0:
        return 0.0

    # Calculate Gini using the area formula
    # Gini = 1 - 2 * (area under Lorenz curve)
    lorenz_curve = cumulative_weighted_values / total_weighted_value
    weight_fractions = sorted_weights / total_weight

    # Area under Lorenz curve using trapezoidal rule
    area = np.sum(weight_fractions * (lorenz_curve - weight_fractions / 2))

    return float(1 - 2 * area)


class Inequality(Output):
    """Single inequality measure result - represents one database row.

    This is a single-simulation output type that calculates inequality
    metrics for a given income variable, optionally filtered by
    demographic variables.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    simulation: Simulation
    income_variable: str
    entity: str = "household"

    # Optional demographic filters
    filter_variable: str | None = None
    filter_variable_eq: Any | None = None
    filter_variable_leq: Any | None = None
    filter_variable_geq: Any | None = None

    # Results populated by run()
    gini: float | None = None
    top_10_share: float | None = None
    top_1_share: float | None = None
    bottom_50_share: float | None = None

    def run(self):
        """Calculate inequality metrics."""
        # Get income variable info
        income_var_obj = (
            self.simulation.tax_benefit_model_version.get_variable(
                self.income_variable
            )
        )

        # Get target entity data
        target_entity = self.entity
        data = getattr(self.simulation.output_dataset.data, target_entity)

        # Map income variable to target entity if needed
        if income_var_obj.entity != target_entity:
            mapped = self.simulation.output_dataset.data.map_to_entity(
                income_var_obj.entity,
                target_entity,
                columns=[self.income_variable],
            )
            income_series = mapped[self.income_variable]
        else:
            income_series = data[self.income_variable]

        # Get weights
        weight_col = f"{target_entity}_weight"
        if weight_col in data.columns:
            weights = data[weight_col]
        else:
            weights = pd.Series(np.ones(len(income_series)))

        # Apply demographic filter if specified
        if self.filter_variable is not None:
            filter_var_obj = (
                self.simulation.tax_benefit_model_version.get_variable(
                    self.filter_variable
                )
            )

            if filter_var_obj.entity != target_entity:
                filter_mapped = (
                    self.simulation.output_dataset.data.map_to_entity(
                        filter_var_obj.entity,
                        target_entity,
                        columns=[self.filter_variable],
                    )
                )
                filter_series = filter_mapped[self.filter_variable]
            else:
                filter_series = data[self.filter_variable]

            # Build filter mask
            mask = filter_series.notna()
            if self.filter_variable_eq is not None:
                mask &= filter_series == self.filter_variable_eq
            if self.filter_variable_leq is not None:
                mask &= filter_series <= self.filter_variable_leq
            if self.filter_variable_geq is not None:
                mask &= filter_series >= self.filter_variable_geq

            # Apply mask
            income_series = income_series[mask]
            weights = weights[mask]

        # Convert to numpy arrays
        values = np.array(income_series)
        weights_arr = np.array(weights)

        # Remove NaN values
        valid_mask = ~np.isnan(values) & ~np.isnan(weights_arr)
        values = values[valid_mask]
        weights_arr = weights_arr[valid_mask]

        # Calculate Gini coefficient
        self.gini = _gini(values, weights_arr)

        # Calculate income shares
        if len(values) > 0 and weights_arr.sum() > 0:
            total_income = np.sum(values * weights_arr)

            if total_income > 0:
                # Sort by income
                sorted_indices = np.argsort(values)
                sorted_values = values[sorted_indices]
                sorted_weights = weights_arr[sorted_indices]

                # Cumulative weight fractions
                cumulative_weights = np.cumsum(sorted_weights)
                total_weight = cumulative_weights[-1]
                weight_fractions = cumulative_weights / total_weight

                # Top 10% share
                top_10_mask = weight_fractions > 0.9
                self.top_10_share = float(
                    np.sum(
                        sorted_values[top_10_mask]
                        * sorted_weights[top_10_mask]
                    )
                    / total_income
                )

                # Top 1% share
                top_1_mask = weight_fractions > 0.99
                self.top_1_share = float(
                    np.sum(
                        sorted_values[top_1_mask] * sorted_weights[top_1_mask]
                    )
                    / total_income
                )

                # Bottom 50% share
                bottom_50_mask = weight_fractions <= 0.5
                self.bottom_50_share = float(
                    np.sum(
                        sorted_values[bottom_50_mask]
                        * sorted_weights[bottom_50_mask]
                    )
                    / total_income
                )
            else:
                self.top_10_share = 0.0
                self.top_1_share = 0.0
                self.bottom_50_share = 0.0
        else:
            self.top_10_share = 0.0
            self.top_1_share = 0.0
            self.bottom_50_share = 0.0


# Default income variables for each country
UK_INEQUALITY_INCOME_VARIABLE = "equiv_hbai_household_net_income"
US_INEQUALITY_INCOME_VARIABLE = "household_net_income"


def calculate_uk_inequality(
    simulation: Simulation,
    income_variable: str = UK_INEQUALITY_INCOME_VARIABLE,
    filter_variable: str | None = None,
    filter_variable_eq: Any | None = None,
    filter_variable_leq: Any | None = None,
    filter_variable_geq: Any | None = None,
) -> Inequality:
    """Calculate inequality metrics for a UK simulation.

    Args:
        simulation: The simulation to analyse
        income_variable: Income variable to use (default: equiv_hbai_household_net_income)
        filter_variable: Optional variable to filter by
        filter_variable_eq: Filter for exact match
        filter_variable_leq: Filter for less than or equal
        filter_variable_geq: Filter for greater than or equal

    Returns:
        Inequality object with Gini and income share metrics
    """
    inequality = Inequality(
        simulation=simulation,
        income_variable=income_variable,
        entity="household",
        filter_variable=filter_variable,
        filter_variable_eq=filter_variable_eq,
        filter_variable_leq=filter_variable_leq,
        filter_variable_geq=filter_variable_geq,
    )
    inequality.run()
    return inequality


def calculate_us_inequality(
    simulation: Simulation,
    income_variable: str = US_INEQUALITY_INCOME_VARIABLE,
    filter_variable: str | None = None,
    filter_variable_eq: Any | None = None,
    filter_variable_leq: Any | None = None,
    filter_variable_geq: Any | None = None,
) -> Inequality:
    """Calculate inequality metrics for a US simulation.

    Args:
        simulation: The simulation to analyse
        income_variable: Income variable to use (default: household_net_income)
        filter_variable: Optional variable to filter by
        filter_variable_eq: Filter for exact match
        filter_variable_leq: Filter for less than or equal
        filter_variable_geq: Filter for greater than or equal

    Returns:
        Inequality object with Gini and income share metrics
    """
    inequality = Inequality(
        simulation=simulation,
        income_variable=income_variable,
        entity="household",
        filter_variable=filter_variable,
        filter_variable_eq=filter_variable_eq,
        filter_variable_leq=filter_variable_leq,
        filter_variable_geq=filter_variable_geq,
    )
    inequality.run()
    return inequality
