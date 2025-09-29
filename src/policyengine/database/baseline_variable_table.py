from sqlmodel import Field, SQLModel
from typing import TYPE_CHECKING

from policyengine.models import ModelVersion, BaselineVariable

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
    data_type: str | None = Field(default=None)  # Data type name

    @classmethod
    def convert_from_model(cls, model: BaselineVariable, database: "Database" = None) -> "BaselineVariableTable":
        """Convert a BaselineVariable instance to a BaselineVariableTable instance."""
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
            data_type=model.data_type.__name__ if model.data_type else None,
        )

    def convert_to_model(self, database: "Database" = None) -> BaselineVariable:
        """Convert this BaselineVariableTable instance to a BaselineVariable instance."""
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

        # Convert data_type string back to type
        data_type = None
        if self.data_type:
            try:
                data_type = eval(self.data_type)
            except:
                data_type = None

        return BaselineVariable(
            id=self.id,
            model_version=model_version,
            entity=self.entity,
            label=self.label,
            description=self.description,
            data_type=data_type,
        )


baseline_variable_table_link = TableLink(
    model_cls=BaselineVariable,
    table_cls=BaselineVariableTable,
)
