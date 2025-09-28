from sqlmodel import Field, SQLModel
from typing import TYPE_CHECKING

from policyengine.models import ModelVersion, BaselineVariable
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class BaselineVariableTable(SQLModel, table=True):
    __tablename__ = "baseline_variables"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(primary_key=True)  # Variable name
    model_id: str = Field(
        primary_key=True, foreign_key="models.id"
    )  # Part of composite key
    model_version_id: str = Field(
        foreign_key="model_versions.id", ondelete="CASCADE"
    )
    entity: str = Field(nullable=False)
    label: str | None = Field(default=None)
    description: str | None = Field(default=None)
    data_type: bytes | None = Field(default=None)  # Pickled type

    @classmethod
    def convert_from_model(cls, model: BaselineVariable, database: "Database" = None) -> "BaselineVariableTable":
        """Convert a BaselineVariable instance to a BaselineVariableTable instance."""
        from policyengine.utils.compress import compress_data

        # Ensure foreign objects are persisted if database is provided
        if database and model.model_version:
            database.set(model.model_version, commit=False)

        return cls(
            id=model.id,
            model_id=model.model_version.model.id if model.model_version and model.model_version.model else None,
            model_version_id=model.model_version.id if model.model_version else None,
            entity=model.entity,
            label=model.label,
            description=model.description,
            data_type=compress_data(model.data_type) if model.data_type else None,
        )

    def convert_to_model(self, database: "Database" = None) -> BaselineVariable:
        """Convert this BaselineVariableTable instance to a BaselineVariable instance."""
        from policyengine.utils.compress import decompress_data
        from .model_version_table import ModelVersionTable
        from sqlmodel import select

        # Resolve foreign keys
        model_version = None

        if database and self.model_version_id:
            version_table = database.session.exec(
                select(ModelVersionTable).where(ModelVersionTable.id == self.model_version_id)
            ).first()
            if version_table:
                model_version = version_table.convert_to_model(database)

        return BaselineVariable(
            id=self.id,
            model_version=model_version,
            entity=self.entity,
            label=self.label,
            description=self.description,
            data_type=decompress_data(self.data_type) if self.data_type else None,
        )


baseline_variable_table_link = TableLink(
    model_cls=BaselineVariable,
    table_cls=BaselineVariableTable,
)
