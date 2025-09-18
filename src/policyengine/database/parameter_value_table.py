from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import uuid4
from datetime import datetime
from policyengine.models import ParameterValue
from .link import TableLink


class ParameterValueTable(SQLModel, table=True):
    __tablename__ = "parameter_values"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    parameter_id: str = Field(foreign_key="parameters.id", ondelete="CASCADE")
    value: float = Field(nullable=False)
    start_date: datetime = Field(nullable=False)
    end_date: Optional[datetime] = Field(default=None)


parameter_value_table_link = TableLink(
    model_cls=ParameterValue,
    table_cls=ParameterValueTable,
    model_to_table_custom_transforms=dict(
        parameter_id=lambda pv: pv.parameter.id,
    ),
    table_to_model_custom_transforms={},
)
