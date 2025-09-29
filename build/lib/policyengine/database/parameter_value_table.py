from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlmodel import JSON, Column, Field, SQLModel

from policyengine.models import Parameter, ParameterValue

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class ParameterValueTable(SQLModel, table=True):
    __tablename__ = "parameter_values"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    parameter_id: str = Field(nullable=False)  # Part of composite foreign key
    model_id: str = Field(nullable=False)  # Part of composite foreign key
    policy_id: str | None = Field(default=None, foreign_key="policies.id", ondelete="CASCADE")  # Link to policy
    value: Any | None = Field(
        default=None, sa_column=Column(JSON)
    )  # JSON field for any type
    start_date: datetime = Field(nullable=False)
    end_date: datetime | None = Field(default=None)

    @classmethod
    def convert_from_model(cls, model: ParameterValue, database: "Database" = None) -> "ParameterValueTable":
        """Convert a ParameterValue instance to a ParameterValueTable instance.

        Args:
            model: The ParameterValue instance to convert
            database: The database instance for persisting the parameter if needed

        Returns:
            A ParameterValueTable instance
        """
        import math

        # Ensure the Parameter is persisted if database is provided
        if database and model.parameter:
            database.set(model.parameter, commit=False)

        # Handle special float values
        value = model.value
        if isinstance(value, float):
            if math.isinf(value):
                value = "Infinity" if value > 0 else "-Infinity"
            elif math.isnan(value):
                value = "NaN"

        return cls(
            id=model.id,
            parameter_id=model.parameter.id if model.parameter else None,
            model_id=model.parameter.model.id if model.parameter and model.parameter.model else None,
            value=value,
            start_date=model.start_date,
            end_date=model.end_date,
        )

    def convert_to_model(self, database: "Database" = None) -> ParameterValue:
        """Convert this ParameterValueTable instance to a ParameterValue instance.

        Args:
            database: The database instance for resolving the parameter foreign key

        Returns:
            A ParameterValue instance
        """
        from .parameter_table import ParameterTable
        from sqlmodel import select

        # Resolve the parameter foreign key
        parameter = None
        if database and self.parameter_id and self.model_id:
            param_table = database.session.exec(
                select(ParameterTable).where(
                    ParameterTable.id == self.parameter_id,
                    ParameterTable.model_id == self.model_id
                )
            ).first()
            if param_table:
                parameter = param_table.convert_to_model(database)

        # Handle special string values
        value = self.value
        if value == "Infinity":
            value = float("inf")
        elif value == "-Infinity":
            value = float("-inf")
        elif value == "NaN":
            value = float("nan")

        return ParameterValue(
            id=self.id,
            parameter=parameter,
            value=value,
            start_date=self.start_date,
            end_date=self.end_date,
        )


parameter_value_table_link = TableLink(
    model_cls=ParameterValue,
    table_cls=ParameterValueTable,
)
