from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field


class AggregateTable(SQLModel, table=True):
    __tablename__ = "reportitem_aggregate"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    simulation_id: UUID = Field(foreign_key="simulations.id")
    time_period: str | None = None
    country: str
    variable_id: UUID = Field(foreign_key="variables.id")
    entity_level: str
    filter_variable_id: UUID | None = Field(default=None, foreign_key="variables.id")
    filter_variable_value: Any | None = Field(default=None, sa_type=JSON)
    filter_variable_min_value: float | None = None
    filter_variable_max_value: float | None = None
    metric: str
    value: float


class CountTable(SQLModel, table=True):
    __tablename__ = "reportitem_count"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    simulation_id: UUID = Field(foreign_key="simulations.id")
    time_period: str | None = None
    country: str
    variable_id: UUID = Field(foreign_key="variables.id")
    entity_level: str
    equals_value: Any | None = Field(default=None, sa_type=JSON)
    min_value: float | None = None
    max_value: float | None = None
    count: float


class ChangeByBaselineGroupTable(SQLModel, table=True):
    __tablename__ = "reportitem_change_by_baseline_group"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    baseline_simulation_id: UUID = Field(foreign_key="simulations.id")
    reform_simulation_id: UUID = Field(foreign_key="simulations.id")
    country: str
    variable_id: UUID = Field(foreign_key="variables.id")
    group_variable_id: UUID = Field(foreign_key="variables.id")
    group_value: Any | None = Field(default=None, sa_type=JSON)
    entity_level: str
    time_period: str | None = None
    total_change: float
    relative_change: float
    average_change_per_entity: float


class VariableChangeGroupByQuantileGroupTable(SQLModel, table=True):
    __tablename__ = "reportitem_varchg_by_quantile_group"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    baseline_simulation_id: UUID = Field(foreign_key="simulations.id")
    reform_simulation_id: UUID = Field(foreign_key="simulations.id")
    country: str
    variable_id: UUID = Field(foreign_key="variables.id")
    group_variable_id: UUID = Field(foreign_key="variables.id")
    quantile_group: int
    quantile_group_count: int
    change_lower_bound: float
    change_upper_bound: float
    change_bound_is_relative: bool
    fixed_entity_count_per_quantile_group: str
    percent_of_group_in_change_group: float
    entities_in_group_in_change_group: float


class VariableChangeGroupByVariableValueTable(SQLModel, table=True):
    __tablename__ = "reportitem_varchg_by_value"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    baseline_simulation_id: UUID = Field(foreign_key="simulations.id")
    reform_simulation_id: UUID = Field(foreign_key="simulations.id")
    country: str
    variable_id: UUID = Field(foreign_key="variables.id")
    group_variable_id: UUID = Field(foreign_key="variables.id")
    group_variable_value: Any | None = Field(default=None, sa_type=JSON)
    change_lower_bound: float
    change_upper_bound: float
    change_bound_is_relative: bool
    fixed_entity_count_per_quantile_group: str
    percent_of_group_in_change_group: float
    entities_in_group_in_change_group: float
