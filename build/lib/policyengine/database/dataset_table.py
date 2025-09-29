from typing import TYPE_CHECKING
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.models import Dataset, Model, VersionedDataset
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


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

    @classmethod
    def convert_from_model(cls, model: Dataset, database: "Database" = None) -> "DatasetTable":
        """Convert a Dataset instance to a DatasetTable instance.

        Args:
            model: The Dataset instance to convert
            database: The database instance for persisting foreign objects if needed

        Returns:
            A DatasetTable instance
        """
        # Ensure foreign objects are persisted if database is provided
        if database:
            if model.versioned_dataset:
                database.set(model.versioned_dataset, commit=False)
            if model.model:
                database.set(model.model, commit=False)

        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
            version=model.version,
            versioned_dataset_id=model.versioned_dataset.id if model.versioned_dataset else None,
            year=model.year,
            data=compress_data(model.data) if model.data else None,
            model_id=model.model.id if model.model else None,
        )

    def convert_to_model(self, database: "Database" = None) -> Dataset:
        """Convert this DatasetTable instance to a Dataset instance.

        Args:
            database: The database instance for resolving foreign keys

        Returns:
            A Dataset instance
        """
        # Resolve foreign keys
        versioned_dataset = None
        model = None

        if database:
            if self.versioned_dataset_id:
                versioned_dataset = database.get(VersionedDataset, id=self.versioned_dataset_id)
            if self.model_id:
                model = database.get(Model, id=self.model_id)

        return Dataset(
            id=self.id,
            name=self.name,
            description=self.description,
            version=self.version,
            versioned_dataset=versioned_dataset,
            year=self.year,
            data=decompress_data(self.data) if self.data else None,
            model=model,
        )


dataset_table_link = TableLink(
    model_cls=Dataset,
    table_cls=DatasetTable,
)
