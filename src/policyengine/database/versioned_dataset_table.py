from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import uuid4
from policyengine.models import VersionedDataset
from .link import TableLink


class VersionedDatasetTable(SQLModel, table=True):
    __tablename__ = "versioned_datasets"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: str = Field(nullable=False)
    model_id: Optional[str] = Field(
        default=None, foreign_key="models.id", ondelete="SET NULL"
    )


versioned_dataset_table_link = TableLink(
    model_cls=VersionedDataset,
    table_cls=VersionedDatasetTable,
    model_to_table_custom_transforms=dict(
        model_id=lambda vd: vd.model.id if vd.model else None,
    ),
    table_to_model_custom_transforms={},
)
