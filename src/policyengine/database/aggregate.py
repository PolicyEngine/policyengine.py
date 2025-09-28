from typing import TYPE_CHECKING
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.database.link import TableLink
from policyengine.models.aggregate import Aggregate
from policyengine.models import Simulation

if TYPE_CHECKING:
    from .database import Database


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
    reportelement_id: str | None = None
    value: float | None = None

    @classmethod
    def convert_from_model(cls, model: Aggregate, database: "Database" = None) -> "AggregateTable":
        """Convert an Aggregate instance to an AggregateTable instance.

        Args:
            model: The Aggregate instance to convert
            database: The database instance for persisting the simulation if needed

        Returns:
            An AggregateTable instance
        """
        # Don't try to save the simulation here - it's already being saved
        # This prevents circular references

        return cls(
            id=model.id,
            simulation_id=model.simulation.id if model.simulation else None,
            entity=model.entity,
            variable_name=model.variable_name,
            year=model.year,
            filter_variable_name=model.filter_variable_name,
            filter_variable_value=model.filter_variable_value,
            filter_variable_leq=model.filter_variable_leq,
            filter_variable_geq=model.filter_variable_geq,
            aggregate_function=model.aggregate_function,
            reportelement_id=model.reportelement_id,
            value=model.value,
        )

    def convert_to_model(self, database: "Database" = None) -> Aggregate:
        """Convert this AggregateTable instance to an Aggregate instance.

        Args:
            database: The database instance for resolving the simulation foreign key

        Returns:
            An Aggregate instance
        """
        from .simulation_table import SimulationTable
        from sqlmodel import select

        # Resolve the simulation foreign key
        simulation = None
        if database and self.simulation_id:
            sim_table = database.session.exec(
                select(SimulationTable).where(SimulationTable.id == self.simulation_id)
            ).first()
            if sim_table:
                simulation = sim_table.convert_to_model(database)

        return Aggregate(
            id=self.id,
            simulation=simulation,
            entity=self.entity,
            variable_name=self.variable_name,
            year=self.year,
            filter_variable_name=self.filter_variable_name,
            filter_variable_value=self.filter_variable_value,
            filter_variable_leq=self.filter_variable_leq,
            filter_variable_geq=self.filter_variable_geq,
            aggregate_function=self.aggregate_function,
            reportelement_id=self.reportelement_id,
            value=self.value,
        )


aggregate_table_link = TableLink(
    model_cls=Aggregate,
    table_cls=AggregateTable,
)
