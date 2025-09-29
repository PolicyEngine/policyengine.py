from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.models import Dynamic
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class DynamicTable(SQLModel, table=True):
    __tablename__ = "dynamics"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    simulation_modifier: bytes | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def convert_from_model(cls, model: Dynamic, database: "Database" = None) -> "DynamicTable":
        """Convert a Dynamic instance to a DynamicTable instance.

        Args:
            model: The Dynamic instance to convert
            database: The database instance (not used for this table)

        Returns:
            A DynamicTable instance
        """
        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
            simulation_modifier=compress_data(model.simulation_modifier) if model.simulation_modifier else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def convert_to_model(self, database: "Database" = None) -> Dynamic:
        """Convert this DynamicTable instance to a Dynamic instance.

        Args:
            database: The database instance (not used for this table)

        Returns:
            A Dynamic instance
        """
        return Dynamic(
            id=self.id,
            name=self.name,
            description=self.description,
            simulation_modifier=decompress_data(self.simulation_modifier) if self.simulation_modifier else None,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


dynamic_table_link = TableLink(
    model_cls=Dynamic,
    table_cls=DynamicTable,
)
