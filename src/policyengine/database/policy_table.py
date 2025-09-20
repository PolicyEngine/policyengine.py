from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.models import Policy
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink


class PolicyTable(SQLModel, table=True):
    __tablename__ = "policies"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    simulation_modifier: bytes | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


policy_table_link = TableLink(
    model_cls=Policy,
    table_cls=PolicyTable,
    model_to_table_custom_transforms=dict(
        simulation_modifier=lambda p: compress_data(p.simulation_modifier)
        if p.simulation_modifier
        else None,
    ),
    table_to_model_custom_transforms=dict(
        simulation_modifier=lambda b: decompress_data(b) if b else None,
    ),
)
