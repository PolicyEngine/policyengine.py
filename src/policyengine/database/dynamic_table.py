from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.models import Dynamic
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink


class DynamicTable(SQLModel, table=True):
    __tablename__ = "dynamics"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    simulation_modifier: bytes | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


dynamic_table_link = TableLink(
    model_cls=Dynamic,
    table_cls=DynamicTable,
    model_to_table_custom_transforms=dict(
        simulation_modifier=lambda d: compress_data(d.simulation_modifier)
        if d.simulation_modifier
        else None,
    ),
    table_to_model_custom_transforms=dict(
        simulation_modifier=lambda b: decompress_data(b) if b else None,
    ),
)
