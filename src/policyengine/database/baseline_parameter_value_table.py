from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import uuid4
from datetime import datetime
from policyengine.models import BaselineParameterValue
from .link import TableLink


class BaselineParameterValueTable(SQLModel, table=True):
    __tablename__ = "baseline_parameter_values"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    parameter_id: str = Field(foreign_key="parameters.id", ondelete="CASCADE")
    model_version_id: str = Field(foreign_key="model_versions.id", ondelete="CASCADE")
    value: Optional[str] = Field(default=None)  # JSON-encoded value
    start_date: datetime = Field(nullable=False)
    end_date: Optional[datetime] = Field(default=None)


baseline_parameter_value_table_link = TableLink(
    model_cls=BaselineParameterValue,
    table_cls=BaselineParameterValueTable,
    model_to_table_custom_transforms=dict(
        parameter_id=lambda bpv: bpv.parameter.id,
        model_version_id=lambda bpv: bpv.model_version.id,
        value=lambda bpv: str(bpv.value) if bpv.value is not None else None,
    ),
    table_to_model_custom_transforms={},
)