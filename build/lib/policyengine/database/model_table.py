from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

from policyengine.models import Model
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class ModelTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "models"

    id: str = Field(primary_key=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    simulation_function: bytes

    @classmethod
    def convert_from_model(cls, model: Model, database: "Database" = None) -> "ModelTable":
        """Convert a Model instance to a ModelTable instance.

        Args:
            model: The Model instance to convert
            database: The database instance (not used for this table)

        Returns:
            A ModelTable instance
        """
        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
            simulation_function=compress_data(model.simulation_function),
        )

    def convert_to_model(self, database: "Database" = None) -> Model:
        """Convert this ModelTable instance to a Model instance.

        Args:
            database: The database instance (not used for this table)

        Returns:
            A Model instance
        """
        return Model(
            id=self.id,
            name=self.name,
            description=self.description,
            simulation_function=decompress_data(self.simulation_function),
        )


model_table_link = TableLink(
    model_cls=Model,
    table_cls=ModelTable,
)
