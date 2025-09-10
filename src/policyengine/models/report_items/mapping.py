"""Mapping utilities between report item models and database tables.

This module provides functions to convert between:
- Pydantic models that use variable names (for computation)
- Database tables that use variable_id UUIDs (for storage)
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from policyengine.tables.variable import VariableTable
from policyengine.tables.report_items import (
    AggregateTable,
    CountTable, 
    ChangeByBaselineGroupTable,
    VariableChangeGroupByQuantileGroupTable,
    VariableChangeGroupByVariableValueTable,
)
from policyengine.models.report_items.aggregate import Aggregate
from policyengine.models.report_items.count import Count
from policyengine.models.report_items.two_sim_change import (
    ChangeByBaselineGroup,
    VariableChangeGroupByQuantileGroup,
    VariableChangeGroupByVariableValue,
)


def get_variable_id(
    session: Session, variable_name: str, country: str
) -> UUID | None:
    """Get variable ID from name and country."""
    variable = session.query(VariableTable).filter(
        VariableTable.name == variable_name,
        VariableTable.country == country
    ).first()
    return variable.id if variable else None


def aggregate_to_table(
    item: Aggregate, session: Session, simulation_id: UUID
) -> AggregateTable:
    """Convert Aggregate model to database table entry."""
    variable_id = get_variable_id(session, item.variable, item.country)
    filter_variable_id = None
    if item.filter_variable:
        filter_variable_id = get_variable_id(
            session, item.filter_variable, item.country
        )
    
    return AggregateTable(
        simulation_id=simulation_id,
        time_period=str(item.time_period) if item.time_period else None,
        country=item.country,
        variable_id=variable_id,
        entity_level=item.entity_level,
        filter_variable_id=filter_variable_id,
        filter_variable_value=item.filter_variable_value,
        filter_variable_min_value=item.filter_variable_min_value,
        filter_variable_max_value=item.filter_variable_max_value,
        metric=item.metric.value,
        value=item.value,
    )


def count_to_table(
    item: Count, session: Session, simulation_id: UUID
) -> CountTable:
    """Convert Count model to database table entry."""
    variable_id = get_variable_id(session, item.variable, item.country)
    
    return CountTable(
        simulation_id=simulation_id,
        time_period=str(item.time_period) if item.time_period else None,
        country=item.country,
        variable_id=variable_id,
        entity_level=item.entity_level,
        equals_value=item.equals_value,
        min_value=item.min_value,
        max_value=item.max_value,
        count=item.count,
    )


def change_by_baseline_group_to_table(
    item: ChangeByBaselineGroup,
    session: Session,
    baseline_simulation_id: UUID,
    reform_simulation_id: UUID,
) -> ChangeByBaselineGroupTable:
    """Convert ChangeByBaselineGroup model to database table entry."""
    variable_id = get_variable_id(session, item.variable, item.country)
    group_variable_id = get_variable_id(session, item.group_variable, item.country)
    
    return ChangeByBaselineGroupTable(
        baseline_simulation_id=baseline_simulation_id,
        reform_simulation_id=reform_simulation_id,
        country=item.country,
        variable_id=variable_id,
        group_variable_id=group_variable_id,
        group_value=item.group_value,
        entity_level=item.entity_level,
        time_period=str(item.time_period) if item.time_period else None,
        total_change=item.total_change,
        relative_change=item.relative_change,
        average_change_per_entity=item.average_change_per_entity,
    )


def variable_change_group_by_quantile_to_table(
    item: VariableChangeGroupByQuantileGroup,
    session: Session,
    baseline_simulation_id: UUID,
    reform_simulation_id: UUID,
) -> VariableChangeGroupByQuantileGroupTable:
    """Convert VariableChangeGroupByQuantileGroup model to database table entry."""
    variable_id = get_variable_id(session, item.variable, item.country)
    group_variable_id = get_variable_id(session, item.group_variable, item.country)
    
    return VariableChangeGroupByQuantileGroupTable(
        baseline_simulation_id=baseline_simulation_id,
        reform_simulation_id=reform_simulation_id,
        country=item.country,
        variable_id=variable_id,
        group_variable_id=group_variable_id,
        quantile_group=item.quantile_group,
        quantile_group_count=item.quantile_group_count,
        change_lower_bound=item.change_lower_bound,
        change_upper_bound=item.change_upper_bound,
        change_bound_is_relative=item.change_bound_is_relative,
        fixed_entity_count_per_quantile_group=item.fixed_entity_count_per_quantile_group,
        percent_of_group_in_change_group=item.percent_of_group_in_change_group,
        entities_in_group_in_change_group=item.entities_in_group_in_change_group,
    )


def variable_change_group_by_value_to_table(
    item: VariableChangeGroupByVariableValue,
    session: Session,
    baseline_simulation_id: UUID,
    reform_simulation_id: UUID,
) -> VariableChangeGroupByVariableValueTable:
    """Convert VariableChangeGroupByVariableValue model to database table entry."""
    variable_id = get_variable_id(session, item.variable, item.country)
    group_variable_id = get_variable_id(session, item.group_variable, item.country)
    
    return VariableChangeGroupByVariableValueTable(
        baseline_simulation_id=baseline_simulation_id,
        reform_simulation_id=reform_simulation_id,
        country=item.country,
        variable_id=variable_id,
        group_variable_id=group_variable_id,
        group_variable_value=item.group_variable_value,
        change_lower_bound=item.change_lower_bound,
        change_upper_bound=item.change_upper_bound,
        change_bound_is_relative=item.change_bound_is_relative,
        fixed_entity_count_per_quantile_group=item.fixed_entity_count_per_quantile_group,
        percent_of_group_in_change_group=item.percent_of_group_in_change_group,
        entities_in_group_in_change_group=item.entities_in_group_in_change_group,
    )