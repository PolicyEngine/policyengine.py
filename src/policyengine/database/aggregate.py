from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.database.link import TableLink
from policyengine.models.aggregate import Aggregate


class AggregateTable(SQLModel, table=True):
    __tablename__ = "aggregates"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    simulation_id: str = Field(
        foreign_key="simulations.id", ondelete="CASCADE"
    )
    entity: str
    variable_name: str
    year: int | None = None
    filter_variable_name: str | None = None
    filter_variable_value: str | None = None
    filter_variable_leq: float | None = None
    filter_variable_geq: float | None = None
    aggregate_function: str
    value: float | None = None


aggregate_table_link = TableLink(
    model_cls=Aggregate,
    table_cls=AggregateTable,
    model_to_table_custom_transforms=dict(
        simulation_id=lambda a: a.simulation.id,
    ),
)
