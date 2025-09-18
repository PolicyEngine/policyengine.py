from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import uuid4
from policyengine.models import Parameter
from .link import TableLink
from policyengine.utils.compress import compress_data, decompress_data


class ParameterTable(SQLModel, table=True):
    __tablename__ = "parameters"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    description: str | None = Field(default=None)
    data_type: Optional[str] = Field(nullable=False)  # Pickled type
    model_id: Optional[str] = Field(
        default=None, foreign_key="models.id", ondelete="SET NULL"
    )


parameter_table_link = TableLink(
    model_cls=Parameter,
    table_cls=ParameterTable,
    model_to_table_custom_transforms=dict(
        data_type=str,
        model_id=lambda p: p.model.id if p.model else None,
    ),
    table_to_model_custom_transforms=dict(
        data_type=type,
    ),
)
