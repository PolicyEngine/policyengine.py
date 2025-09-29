from uuid import uuid4

from sqlmodel import Field, SQLModel
from typing import TYPE_CHECKING

from policyengine.models import VersionedDataset

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class VersionedDatasetTable(SQLModel, table=True):
    __tablename__ = "versioned_datasets"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: str = Field(nullable=False)
    model_id: str | None = Field(
        default=None, foreign_key="models.id", ondelete="SET NULL"
    )

    @classmethod
    def convert_from_model(cls, model: VersionedDataset, database: "Database" = None) -> "VersionedDatasetTable":
        """Convert a VersionedDataset instance to a VersionedDatasetTable instance."""
        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
        )

    def convert_to_model(self, database: "Database" = None) -> VersionedDataset:
        """Convert this VersionedDatasetTable instance to a VersionedDataset instance."""
        return VersionedDataset(
            id=self.id,
            name=self.name,
            description=self.description,
        )


versioned_dataset_table_link = TableLink(
    model_cls=VersionedDataset,
    table_cls=VersionedDatasetTable,
)
