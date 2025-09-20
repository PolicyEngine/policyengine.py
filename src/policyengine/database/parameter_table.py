from sqlmodel import Field, SQLModel

from policyengine.models import Parameter

from .link import TableLink


class ParameterTable(SQLModel, table=True):
    __tablename__ = "parameters"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(primary_key=True)  # Parameter name
    model_id: str = Field(
        primary_key=True, foreign_key="models.id"
    )  # Part of composite key
    description: str | None = Field(default=None)
    data_type: str | None = Field(nullable=True)  # Data type name


parameter_table_link = TableLink(
    model_cls=Parameter,
    table_cls=ParameterTable,
    primary_key=("id", "model_id"),  # Composite primary key
    model_to_table_custom_transforms=dict(
        data_type=lambda p: p.data_type.__name__ if p.data_type else None,
        model_id=lambda p: p.model.id if p.model else None,
    ),
    table_to_model_custom_transforms=dict(
        data_type=lambda t: eval(t.data_type) if t.data_type else None
    ),
)
