from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

from policyengine.models import Model, Parameter

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class ParameterTable(SQLModel, table=True):
    __tablename__ = "parameters"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(primary_key=True)  # Parameter name
    model_id: str = Field(
        primary_key=True, foreign_key="models.id"
    )  # Part of composite key
    description: str | None = Field(default=None)
    data_type: str | None = Field(nullable=True)  # Data type name
    label: str | None = Field(default=None)
    unit: str | None = Field(default=None)

    @classmethod
    def convert_from_model(cls, model: Parameter, database: "Database" = None) -> "ParameterTable":
        """Convert a Parameter instance to a ParameterTable instance.

        Args:
            model: The Parameter instance to convert
            database: The database instance for persisting the model if needed

        Returns:
            A ParameterTable instance
        """
        # Ensure the Model is persisted if database is provided
        if database and model.model:
            database.set(model.model, commit=False)

        return cls(
            id=model.id,
            model_id=model.model.id if model.model else None,
            description=model.description,
            data_type=model.data_type.__name__ if model.data_type else None,
            label=model.label,
            unit=model.unit,
        )

    def convert_to_model(self, database: "Database" = None) -> Parameter:
        """Convert this ParameterTable instance to a Parameter instance.

        Args:
            database: The database instance for resolving the model foreign key

        Returns:
            A Parameter instance
        """
        from .model_table import ModelTable
        from sqlmodel import select

        # Resolve the model foreign key
        model = None
        if database and self.model_id:
            model_table = database.session.exec(
                select(ModelTable).where(ModelTable.id == self.model_id)
            ).first()
            if model_table:
                model = model_table.convert_to_model(database)

        # Convert data_type string back to type
        data_type = None
        if self.data_type:
            try:
                data_type = eval(self.data_type)
            except:
                data_type = None

        return Parameter(
            id=self.id,
            description=self.description,
            data_type=data_type,
            model=model,
            label=self.label,
            unit=self.unit,
        )


parameter_table_link = TableLink(
    model_cls=Parameter,
    table_cls=ParameterTable,
)
