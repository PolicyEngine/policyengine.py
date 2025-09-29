from typing import TYPE_CHECKING
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.database.link import TableLink
from policyengine.models.aggregate_change import AggregateChange

if TYPE_CHECKING:
    from .database import Database


class AggregateChangeTable(SQLModel, table=True):
    __tablename__ = "aggregate_changes"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    baseline_simulation_id: str = Field(
        foreign_key="simulations.id", ondelete="CASCADE"
    )
    comparison_simulation_id: str = Field(
        foreign_key="simulations.id", ondelete="CASCADE"
    )
    entity: str
    variable_name: str
    year: int | None = None
    filter_variable_name: str | None = None
    filter_variable_value: str | None = None
    filter_variable_leq: float | None = None
    filter_variable_geq: float | None = None
    filter_variable_quantile_leq: float | None = None
    filter_variable_quantile_geq: float | None = None
    filter_variable_quantile_value: str | None = None
    aggregate_function: str
    reportelement_id: str | None = None

    baseline_value: float | None = None
    comparison_value: float | None = None
    change: float | None = None
    relative_change: float | None = None

    @classmethod
    def convert_from_model(cls, model: AggregateChange, database: "Database" = None) -> "AggregateChangeTable":
        """Convert an AggregateChange instance to an AggregateChangeTable instance.

        Args:
            model: The AggregateChange instance to convert
            database: The database instance for persisting the simulations if needed

        Returns:
            An AggregateChangeTable instance
        """
        return cls(
            id=model.id,
            baseline_simulation_id=model.baseline_simulation.id if model.baseline_simulation else None,
            comparison_simulation_id=model.comparison_simulation.id if model.comparison_simulation else None,
            entity=model.entity,
            variable_name=model.variable_name,
            year=model.year,
            filter_variable_name=model.filter_variable_name,
            filter_variable_value=model.filter_variable_value,
            filter_variable_leq=model.filter_variable_leq,
            filter_variable_geq=model.filter_variable_geq,
            filter_variable_quantile_leq=model.filter_variable_quantile_leq,
            filter_variable_quantile_geq=model.filter_variable_quantile_geq,
            filter_variable_quantile_value=model.filter_variable_quantile_value,
            aggregate_function=model.aggregate_function,
            reportelement_id=model.reportelement_id,
            baseline_value=model.baseline_value,
            comparison_value=model.comparison_value,
            change=model.change,
            relative_change=model.relative_change,
        )

    def convert_to_model(self, database: "Database" = None) -> AggregateChange:
        """Convert this AggregateChangeTable instance to an AggregateChange instance.

        Args:
            database: The database instance for resolving simulation foreign keys

        Returns:
            An AggregateChange instance
        """
        from .simulation_table import SimulationTable
        from sqlmodel import select

        # Resolve the simulation foreign keys
        baseline_simulation = None
        comparison_simulation = None

        if database:
            if self.baseline_simulation_id:
                sim_table = database.session.exec(
                    select(SimulationTable).where(SimulationTable.id == self.baseline_simulation_id)
                ).first()
                if sim_table:
                    baseline_simulation = sim_table.convert_to_model(database)

            if self.comparison_simulation_id:
                sim_table = database.session.exec(
                    select(SimulationTable).where(SimulationTable.id == self.comparison_simulation_id)
                ).first()
                if sim_table:
                    comparison_simulation = sim_table.convert_to_model(database)

        return AggregateChange(
            id=self.id,
            baseline_simulation=baseline_simulation,
            comparison_simulation=comparison_simulation,
            entity=self.entity,
            variable_name=self.variable_name,
            year=self.year,
            filter_variable_name=self.filter_variable_name,
            filter_variable_value=self.filter_variable_value,
            filter_variable_leq=self.filter_variable_leq,
            filter_variable_geq=self.filter_variable_geq,
            filter_variable_quantile_leq=self.filter_variable_quantile_leq,
            filter_variable_quantile_geq=self.filter_variable_quantile_geq,
            filter_variable_quantile_value=self.filter_variable_quantile_value,
            aggregate_function=self.aggregate_function,
            reportelement_id=self.reportelement_id,
            baseline_value=self.baseline_value,
            comparison_value=self.comparison_value,
            change=self.change,
            relative_change=self.relative_change,
        )


aggregate_change_table_link = TableLink(
    model_cls=AggregateChange,
    table_cls=AggregateChangeTable,
)