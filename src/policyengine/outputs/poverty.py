"""Poverty analysis output types."""

from enum import StrEnum
from typing import Any

import pandas as pd
from pydantic import ConfigDict

from policyengine.core import Output, OutputCollection, Simulation


class UKPovertyType(StrEnum):
    """UK poverty measure types."""

    ABSOLUTE_BHC = "absolute_bhc"
    ABSOLUTE_AHC = "absolute_ahc"
    RELATIVE_BHC = "relative_bhc"
    RELATIVE_AHC = "relative_ahc"


class USPovertyType(StrEnum):
    """US poverty measure types."""

    SPM = "spm"
    SPM_DEEP = "spm_deep"


# Mapping from poverty type to variable name
UK_POVERTY_VARIABLES = {
    UKPovertyType.ABSOLUTE_BHC: "in_poverty_bhc",
    UKPovertyType.ABSOLUTE_AHC: "in_poverty_ahc",
    UKPovertyType.RELATIVE_BHC: "in_relative_poverty_bhc",
    UKPovertyType.RELATIVE_AHC: "in_relative_poverty_ahc",
}

US_POVERTY_VARIABLES = {
    USPovertyType.SPM: "spm_unit_is_in_spm_poverty",
    USPovertyType.SPM_DEEP: "spm_unit_is_in_deep_spm_poverty",
}


class Poverty(Output):
    """Single poverty measure result - represents one database row.

    This is a single-simulation output type that calculates poverty
    headcount and rate for a given poverty measure, optionally filtered
    by demographic variables.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    simulation: Simulation
    poverty_variable: str
    entity: str = "person"

    # Optional demographic filters
    filter_variable: str | None = None
    filter_variable_eq: Any | None = None
    filter_variable_leq: Any | None = None
    filter_variable_geq: Any | None = None

    # Results populated by run()
    headcount: float | None = None
    total_population: float | None = None
    rate: float | None = None

    def run(self):
        """Calculate poverty headcount and rate."""
        # Get poverty variable info
        poverty_var_obj = (
            self.simulation.tax_benefit_model_version.get_variable(
                self.poverty_variable
            )
        )

        # Get target entity data
        target_entity = self.entity
        data = getattr(self.simulation.output_dataset.data, target_entity)

        # Map poverty variable to target entity if needed
        if poverty_var_obj.entity != target_entity:
            mapped = self.simulation.output_dataset.data.map_to_entity(
                poverty_var_obj.entity,
                target_entity,
                columns=[self.poverty_variable],
            )
            poverty_series = mapped[self.poverty_variable]
        else:
            poverty_series = data[self.poverty_variable]

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
            poverty_series = poverty_series[mask]

        # Calculate results using weighted counts
        self.headcount = float((poverty_series == True).sum())  # noqa: E712
        self.total_population = float(poverty_series.count())
        self.rate = (
            self.headcount / self.total_population
            if self.total_population > 0
            else 0.0
        )


def calculate_uk_poverty_rates(
    simulation: Simulation,
    filter_variable: str | None = None,
    filter_variable_eq: Any | None = None,
    filter_variable_leq: Any | None = None,
    filter_variable_geq: Any | None = None,
) -> OutputCollection[Poverty]:
    """Calculate all UK poverty rates for a simulation.

    Args:
        simulation: The simulation to analyse
        filter_variable: Optional variable to filter by (e.g., "is_child")
        filter_variable_eq: Filter for exact match
        filter_variable_leq: Filter for less than or equal
        filter_variable_geq: Filter for greater than or equal

    Returns:
        OutputCollection containing Poverty objects for each UK poverty type
    """
    results = []

    for poverty_variable in UK_POVERTY_VARIABLES.values():
        poverty = Poverty(
            simulation=simulation,
            poverty_variable=poverty_variable,
            entity="person",
            filter_variable=filter_variable,
            filter_variable_eq=filter_variable_eq,
            filter_variable_leq=filter_variable_leq,
            filter_variable_geq=filter_variable_geq,
        )
        poverty.run()
        results.append(poverty)

    df = pd.DataFrame(
        [
            {
                "simulation_id": r.simulation.id,
                "poverty_variable": r.poverty_variable,
                "filter_variable": r.filter_variable,
                "filter_variable_eq": r.filter_variable_eq,
                "filter_variable_leq": r.filter_variable_leq,
                "filter_variable_geq": r.filter_variable_geq,
                "headcount": r.headcount,
                "total_population": r.total_population,
                "rate": r.rate,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)


def calculate_us_poverty_rates(
    simulation: Simulation,
    filter_variable: str | None = None,
    filter_variable_eq: Any | None = None,
    filter_variable_leq: Any | None = None,
    filter_variable_geq: Any | None = None,
) -> OutputCollection[Poverty]:
    """Calculate all US poverty rates for a simulation.

    Args:
        simulation: The simulation to analyse
        filter_variable: Optional variable to filter by (e.g., "is_child")
        filter_variable_eq: Filter for exact match
        filter_variable_leq: Filter for less than or equal
        filter_variable_geq: Filter for greater than or equal

    Returns:
        OutputCollection containing Poverty objects for each US poverty type
    """
    results = []

    for poverty_variable in US_POVERTY_VARIABLES.values():
        poverty = Poverty(
            simulation=simulation,
            poverty_variable=poverty_variable,
            entity="person",
            filter_variable=filter_variable,
            filter_variable_eq=filter_variable_eq,
            filter_variable_leq=filter_variable_leq,
            filter_variable_geq=filter_variable_geq,
        )
        poverty.run()
        results.append(poverty)

    df = pd.DataFrame(
        [
            {
                "simulation_id": r.simulation.id,
                "poverty_variable": r.poverty_variable,
                "filter_variable": r.filter_variable,
                "filter_variable_eq": r.filter_variable_eq,
                "filter_variable_leq": r.filter_variable_leq,
                "filter_variable_geq": r.filter_variable_geq,
                "headcount": r.headcount,
                "total_population": r.total_population,
                "rate": r.rate,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)
