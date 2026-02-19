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
    poverty_type: str | None = None
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

    for poverty_type, poverty_variable in UK_POVERTY_VARIABLES.items():
        poverty = Poverty(
            simulation=simulation,
            poverty_variable=poverty_variable,
            poverty_type=str(poverty_type),
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
                "poverty_type": r.poverty_type,
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

    for poverty_type, poverty_variable in US_POVERTY_VARIABLES.items():
        poverty = Poverty(
            simulation=simulation,
            poverty_variable=poverty_variable,
            poverty_type=str(poverty_type),
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
                "poverty_type": r.poverty_type,
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


# Race group definitions (US only — race Enum stored as string names)
RACE_GROUPS = {
    "white": {"filter_variable": "race", "filter_variable_eq": "WHITE"},
    "black": {"filter_variable": "race", "filter_variable_eq": "BLACK"},
    "hispanic": {"filter_variable": "race", "filter_variable_eq": "HISPANIC"},
    "other": {"filter_variable": "race", "filter_variable_eq": "OTHER"},
}

# Gender group definitions (same for UK and US — both use is_male boolean)
GENDER_GROUPS = {
    "male": {"filter_variable": "is_male", "filter_variable_eq": True},
    "female": {"filter_variable": "is_male", "filter_variable_eq": False},
}

# Age group definitions (same for UK and US)
AGE_GROUPS = {
    "child": {"filter_variable": "age", "filter_variable_leq": 17},
    "adult": {
        "filter_variable": "age",
        "filter_variable_geq": 18,
        "filter_variable_leq": 64,
    },
    "senior": {"filter_variable": "age", "filter_variable_geq": 65},
}


def calculate_uk_poverty_by_age(
    simulation: Simulation,
) -> OutputCollection[Poverty]:
    """Calculate UK poverty rates broken down by age group.

    Computes poverty rates for child (< 18), adult (18-64), and
    senior (65+) groups across all UK poverty types.

    Returns:
        OutputCollection containing Poverty objects for each
        age group x poverty type combination (3 x 4 = 12 records).
    """
    results = []

    for group_name, filters in AGE_GROUPS.items():
        group_results = calculate_uk_poverty_rates(simulation, **filters)
        for pov in group_results.outputs:
            pov.filter_variable = group_name
            results.append(pov)

    df = pd.DataFrame(
        [
            {
                "simulation_id": r.simulation.id,
                "poverty_type": r.poverty_type,
                "poverty_variable": r.poverty_variable,
                "filter_variable": r.filter_variable,
                "headcount": r.headcount,
                "total_population": r.total_population,
                "rate": r.rate,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)


def calculate_us_poverty_by_age(
    simulation: Simulation,
) -> OutputCollection[Poverty]:
    """Calculate US poverty rates broken down by age group.

    Computes poverty rates for child (< 18), adult (18-64), and
    senior (65+) groups across all US poverty types.

    Returns:
        OutputCollection containing Poverty objects for each
        age group x poverty type combination (3 x 2 = 6 records).
    """
    results = []

    for group_name, filters in AGE_GROUPS.items():
        group_results = calculate_us_poverty_rates(simulation, **filters)
        for pov in group_results.outputs:
            pov.filter_variable = group_name
            results.append(pov)

    df = pd.DataFrame(
        [
            {
                "simulation_id": r.simulation.id,
                "poverty_type": r.poverty_type,
                "poverty_variable": r.poverty_variable,
                "filter_variable": r.filter_variable,
                "headcount": r.headcount,
                "total_population": r.total_population,
                "rate": r.rate,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)


def calculate_uk_poverty_by_gender(
    simulation: Simulation,
) -> OutputCollection[Poverty]:
    """Calculate UK poverty rates broken down by gender.

    Computes poverty rates for male and female groups across
    all UK poverty types using the is_male boolean variable.

    Returns:
        OutputCollection containing Poverty objects for each
        gender x poverty type combination (2 x 4 = 8 records).
    """
    results = []

    for group_name, filters in GENDER_GROUPS.items():
        group_results = calculate_uk_poverty_rates(simulation, **filters)
        for pov in group_results.outputs:
            pov.filter_variable = group_name
            results.append(pov)

    df = pd.DataFrame(
        [
            {
                "simulation_id": r.simulation.id,
                "poverty_type": r.poverty_type,
                "poverty_variable": r.poverty_variable,
                "filter_variable": r.filter_variable,
                "headcount": r.headcount,
                "total_population": r.total_population,
                "rate": r.rate,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)


def calculate_us_poverty_by_gender(
    simulation: Simulation,
) -> OutputCollection[Poverty]:
    """Calculate US poverty rates broken down by gender.

    Computes poverty rates for male and female groups across
    all US poverty types using the is_male boolean variable.

    Returns:
        OutputCollection containing Poverty objects for each
        gender x poverty type combination (2 x 2 = 4 records).
    """
    results = []

    for group_name, filters in GENDER_GROUPS.items():
        group_results = calculate_us_poverty_rates(simulation, **filters)
        for pov in group_results.outputs:
            pov.filter_variable = group_name
            results.append(pov)

    df = pd.DataFrame(
        [
            {
                "simulation_id": r.simulation.id,
                "poverty_type": r.poverty_type,
                "poverty_variable": r.poverty_variable,
                "filter_variable": r.filter_variable,
                "headcount": r.headcount,
                "total_population": r.total_population,
                "rate": r.rate,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)


def calculate_us_poverty_by_race(
    simulation: Simulation,
) -> OutputCollection[Poverty]:
    """Calculate US poverty rates broken down by race.

    Computes poverty rates for white, black, hispanic, and other
    racial groups across all US poverty types using the race Enum
    variable (stored as string names in the output dataset).

    US-only — the UK does not have a race variable.

    Returns:
        OutputCollection containing Poverty objects for each
        race x poverty type combination (4 x 2 = 8 records).
    """
    results = []

    for group_name, filters in RACE_GROUPS.items():
        group_results = calculate_us_poverty_rates(simulation, **filters)
        for pov in group_results.outputs:
            pov.filter_variable = group_name
            results.append(pov)

    df = pd.DataFrame(
        [
            {
                "simulation_id": r.simulation.id,
                "poverty_type": r.poverty_type,
                "poverty_variable": r.poverty_variable,
                "filter_variable": r.filter_variable,
                "headcount": r.headcount,
                "total_population": r.total_population,
                "rate": r.rate,
            }
            for r in results
        ]
    )

    return OutputCollection(outputs=results, dataframe=df)
