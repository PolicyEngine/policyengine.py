from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlmodel import JSON, Column, Field, SQLModel
from typing import TYPE_CHECKING

from policyengine.models import ModelVersion, Parameter, BaselineParameterValue

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class BaselineParameterValueTable(SQLModel, table=True):
    __tablename__ = "baseline_parameter_values"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    parameter_id: str = Field(nullable=False)  # Part of composite foreign key
    model_id: str = Field(nullable=False)  # Part of composite foreign key
    model_version_id: str = Field(
        foreign_key="model_versions.id", ondelete="CASCADE"
    )
    value: Any | None = Field(
        default=None, sa_column=Column(JSON)
    )  # JSON field for any type
    start_date: datetime = Field(nullable=False)
    end_date: datetime | None = Field(default=None)

    @classmethod
    def convert_from_model(cls, model: BaselineParameterValue, database: "Database" = None) -> "BaselineParameterValueTable":
        """Convert a BaselineParameterValue instance to a BaselineParameterValueTable instance."""
        import math

        # Ensure foreign objects are persisted if database is provided
        if database:
            if model.parameter:
                database.set(model.parameter, commit=False)
            if model.model_version:
                database.set(model.model_version, commit=False)

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
            model_version_id=model.model_version.id if model.model_version else None,
            value=value,
            start_date=model.start_date,
            end_date=model.end_date,
        )

    def convert_to_model(self, database: "Database" = None) -> BaselineParameterValue:
        """Convert this BaselineParameterValueTable instance to a BaselineParameterValue instance."""
        from .parameter_table import ParameterTable
        from .model_version_table import ModelVersionTable
        from sqlmodel import select

        # Resolve foreign keys
        parameter = None
        model_version = None

        if database:
            if self.parameter_id and self.model_id:
                param_table = database.session.exec(
                    select(ParameterTable).where(
                        ParameterTable.id == self.parameter_id,
                        ParameterTable.model_id == self.model_id
                    )
                ).first()
                if param_table:
                    parameter = param_table.convert_to_model(database)

            if self.model_version_id:
                version_table = database.session.exec(
                    select(ModelVersionTable).where(ModelVersionTable.id == self.model_version_id)
                ).first()
                if version_table:
                    model_version = version_table.convert_to_model(database)

        # Handle special string values
        value = self.value
        if value == "Infinity":
            value = float("inf")
        elif value == "-Infinity":
            value = float("-inf")
        elif value == "NaN":
            value = float("nan")

        return BaselineParameterValue(
            id=self.id,
            parameter=parameter,
            model_version=model_version,
            value=value,
            start_date=self.start_date,
            end_date=self.end_date,
        )


baseline_parameter_value_table_link = TableLink(
    model_cls=BaselineParameterValue,
    table_cls=BaselineParameterValueTable,
)
