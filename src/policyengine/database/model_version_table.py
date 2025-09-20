from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.models import ModelVersion

from .link import TableLink


class ModelVersionTable(SQLModel, table=True):
    __tablename__ = "model_versions"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    model_id: str = Field(foreign_key="models.id", ondelete="CASCADE")
    version: str = Field(nullable=False)
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)


model_version_table_link = TableLink(
    model_cls=ModelVersion,
    table_cls=ModelVersionTable,
    model_to_table_custom_transforms=dict(
        model_id=lambda model_version: model_version.model.id,
    ),
    table_to_model_custom_transforms={},
)
