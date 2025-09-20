from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlmodel import JSON, Column, Field, SQLModel

from policyengine.models import BaselineParameterValue

from .link import TableLink


class BaselineParameterValueTable(SQLModel, table=True):
    __tablename__ = "baseline_parameter_values"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    parameter_id: str = Field(nullable=False)  # Part of composite foreign key
    model_id: str = Field(nullable=False)  # Part of composite foreign key
    model_version_id: str = Field(
        foreign_key="model_versions.id", ondelete="CASCADE"
    )
    value: Any | None = Field(
        default=None, sa_column=Column(JSON)
    )  # JSON field for any type
    start_date: datetime = Field(nullable=False)
    end_date: datetime | None = Field(default=None)


def transform_value_to_table(bpv):
    """Transform value for storage, handling special float values."""
    import math

    value = bpv.value
    if isinstance(value, float):
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        elif math.isnan(value):
            return "NaN"
    return value


def transform_value_from_table(table_row):
    """Transform value from storage, converting special strings back to floats."""
    value = table_row.value
    if value == "Infinity":
        return float("inf")
    elif value == "-Infinity":
        return float("-inf")
    elif value == "NaN":
        return float("nan")
    return value


baseline_parameter_value_table_link = TableLink(
    model_cls=BaselineParameterValue,
    table_cls=BaselineParameterValueTable,
    model_to_table_custom_transforms=dict(
        parameter_id=lambda bpv: bpv.parameter.id,
        model_id=lambda bpv: bpv.parameter.model.id,  # Add model_id from parameter
        model_version_id=lambda bpv: bpv.model_version.id,
        value=transform_value_to_table,
    ),
    table_to_model_custom_transforms=dict(
        value=transform_value_from_table,
    ),
)
