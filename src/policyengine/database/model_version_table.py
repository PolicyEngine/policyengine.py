from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.models import Model, ModelVersion

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class ModelVersionTable(SQLModel, table=True):
    __tablename__ = "model_versions"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    model_id: str = Field(foreign_key="models.id", ondelete="CASCADE")
    version: str = Field(nullable=False)
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def convert_from_model(cls, model: ModelVersion, database: "Database" = None) -> "ModelVersionTable":
        """Convert a ModelVersion instance to a ModelVersionTable instance.

        Args:
            model: The ModelVersion instance to convert
            database: The database instance for persisting the model if needed

        Returns:
            A ModelVersionTable instance
        """
        # Ensure the Model is persisted if database is provided
        if database and model.model:
            database.set(model.model, commit=False)

        return cls(
            id=model.id,
            model_id=model.model.id if model.model else None,
            version=model.version,
            description=model.description,
            created_at=model.created_at,
        )

    def convert_to_model(self, database: "Database" = None) -> ModelVersion:
        """Convert this ModelVersionTable instance to a ModelVersion instance.

        Args:
            database: The database instance for resolving the model foreign key

        Returns:
            A ModelVersion instance
        """
        # Resolve the model foreign key
        model = None
        if database and self.model_id:
            model = database.get(Model, id=self.model_id)

        return ModelVersion(
            id=self.id,
            model=model,
            version=self.version,
            description=self.description,
            created_at=self.created_at,
        )


model_version_table_link = TableLink(
    model_cls=ModelVersion,
    table_cls=ModelVersionTable,
)
