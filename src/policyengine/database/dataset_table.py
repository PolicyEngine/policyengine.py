from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import uuid4
from policyengine.models import Dataset
from .link import TableLink
from policyengine.utils.compress import compress_data, decompress_data


class DatasetTable(SQLModel, table=True):
    __tablename__ = "datasets"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)
    versioned_dataset_id: Optional[str] = Field(
        default=None, foreign_key="versioned_datasets.id", ondelete="SET NULL"
    )
    year: Optional[int] = Field(default=None)
    data: Optional[bytes] = Field(default=None)
    model_id: Optional[str] = Field(
        default=None, foreign_key="models.id", ondelete="SET NULL"
    )


dataset_table_link = TableLink(
    model_cls=Dataset,
    table_cls=DatasetTable,
    model_to_table_custom_transforms=dict(
        versioned_dataset_id=lambda d: d.versioned_dataset.id
        if d.versioned_dataset
        else None,
        model_id=lambda d: d.model.id if d.model else None,
        data=lambda d: compress_data(d.data) if d.data else None,
    ),
    table_to_model_custom_transforms=dict(
        data=lambda b: decompress_data(b) if b else None,
    ),
)
