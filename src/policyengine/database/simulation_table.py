from sqlmodel import SQLModel, Field
from typing import Optional, Any
from uuid import uuid4
from datetime import datetime
from policyengine.models import Simulation
from .link import TableLink
from policyengine.utils.compress import compress_data, decompress_data


class SimulationTable(SQLModel, table=True):
    __tablename__ = "simulations"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    policy_id: Optional[str] = Field(
        default=None, foreign_key="policies.id", ondelete="SET NULL"
    )
    dynamic_id: Optional[str] = Field(
        default=None, foreign_key="dynamics.id", ondelete="SET NULL"
    )
    dataset_id: str = Field(foreign_key="datasets.id", ondelete="CASCADE")
    model_id: str = Field(foreign_key="models.id", ondelete="CASCADE")
    model_version_id: Optional[str] = Field(
        default=None, foreign_key="model_versions.id", ondelete="SET NULL"
    )

    result: Optional[bytes] = Field(default=None)


simulation_table_link = TableLink(
    model_cls=Simulation,
    table_cls=SimulationTable,
    model_to_table_custom_transforms=dict(
        policy_id=lambda s: s.policy.id if s.policy else None,
        dynamic_id=lambda s: s.dynamic.id if s.dynamic else None,
        dataset_id=lambda s: s.dataset.id,
        model_id=lambda s: s.model.id,
        model_version_id=lambda s: s.model_version.id
        if s.model_version
        else None,
        result=lambda s: compress_data(s.result) if s.result else None,
    ),
    table_to_model_custom_transforms=dict(
        result=lambda b: decompress_data(b) if b else None,
    ),
)
