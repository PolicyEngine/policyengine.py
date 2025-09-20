from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.models import Dataset
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink


class DatasetTable(SQLModel, table=True):
    __tablename__ = "datasets"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    version: str | None = Field(default=None)
    versioned_dataset_id: str | None = Field(
        default=None, foreign_key="versioned_datasets.id", ondelete="SET NULL"
    )
    year: int | None = Field(default=None)
    data: bytes | None = Field(default=None)
    model_id: str | None = Field(
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
