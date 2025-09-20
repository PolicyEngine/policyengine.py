from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlmodel import JSON, Column, Field, SQLModel

from policyengine.models import ParameterValue

from .link import TableLink


class ParameterValueTable(SQLModel, table=True):
    __tablename__ = "parameter_values"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    parameter_id: str = Field(nullable=False)  # Part of composite foreign key
    model_id: str = Field(nullable=False)  # Part of composite foreign key
    value: Any | None = Field(
        default=None, sa_column=Column(JSON)
    )  # JSON field for any type
    start_date: datetime = Field(nullable=False)
    end_date: datetime | None = Field(default=None)


def transform_value_to_table(pv):
    """Transform value for storage, handling special float values."""
    import math

    value = pv.value
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


parameter_value_table_link = TableLink(
    model_cls=ParameterValue,
    table_cls=ParameterValueTable,
    model_to_table_custom_transforms=dict(
        parameter_id=lambda pv: pv.parameter.id,
        model_id=lambda pv: pv.parameter.model.id,  # Add model_id from parameter
        value=transform_value_to_table,
    ),
    table_to_model_custom_transforms=dict(
        value=transform_value_from_table,
    ),
)
