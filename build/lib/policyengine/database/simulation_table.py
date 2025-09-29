from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.models import Dataset, Dynamic, Model, ModelVersion, Policy, Simulation
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class SimulationTable(SQLModel, table=True):
    __tablename__ = "simulations"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    policy_id: str | None = Field(
        default=None, foreign_key="policies.id", ondelete="SET NULL"
    )
    dynamic_id: str | None = Field(
        default=None, foreign_key="dynamics.id", ondelete="SET NULL"
    )
    dataset_id: str = Field(foreign_key="datasets.id", ondelete="CASCADE")
    model_id: str = Field(foreign_key="models.id", ondelete="CASCADE")
    model_version_id: str | None = Field(
        default=None, foreign_key="model_versions.id", ondelete="SET NULL"
    )

    result: bytes | None = Field(default=None)

    @classmethod
    def convert_from_model(cls, model: Simulation, database: "Database" = None) -> "SimulationTable":
        """Convert a Simulation instance to a SimulationTable instance.

        Args:
            model: The Simulation instance to convert
            database: The database instance for persisting foreign objects if needed

        Returns:
            A SimulationTable instance
        """
        # Ensure all foreign objects are persisted if database is provided
        if database:
            if model.policy:
                database.set(model.policy, commit=False)
            if model.dynamic:
                database.set(model.dynamic, commit=False)
            if model.dataset:
                database.set(model.dataset, commit=False)
            if model.model:
                database.set(model.model, commit=False)
            if model.model_version:
                database.set(model.model_version, commit=False)

        sim_table = cls(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            policy_id=model.policy.id if model.policy else None,
            dynamic_id=model.dynamic.id if model.dynamic else None,
            dataset_id=model.dataset.id if model.dataset else None,
            model_id=model.model.id if model.model else None,
            model_version_id=model.model_version.id if model.model_version else None,
            result=compress_data(model.result) if model.result else None,
        )

        # Handle nested aggregates if database is provided
        if database and model.aggregates:
            from .aggregate import AggregateTable
            from sqlmodel import select

            # First ensure the simulation table is saved to the database
            # This is necessary so the foreign key constraint is satisfied
            # Check if it already exists
            existing_sim = database.session.exec(
                select(SimulationTable).where(SimulationTable.id == model.id)
            ).first()

            if not existing_sim:
                database.session.add(sim_table)
                database.session.flush()

            # Track which aggregate IDs we want to keep
            desired_agg_ids = {agg.id for agg in model.aggregates}

            # Delete only aggregates linked to this simulation that are NOT in the new list
            existing_aggs = database.session.exec(
                select(AggregateTable).where(AggregateTable.simulation_id == model.id)
            ).all()
            for agg in existing_aggs:
                if agg.id not in desired_agg_ids:
                    database.session.delete(agg)

            # Now save/update the aggregates
            for aggregate in model.aggregates:
                # Check if this aggregate already exists in the database
                existing_agg = database.session.exec(
                    select(AggregateTable).where(AggregateTable.id == aggregate.id)
                ).first()

                if existing_agg:
                    # Update existing aggregate
                    agg_table = AggregateTable.convert_from_model(aggregate, database)
                    existing_agg.simulation_id = agg_table.simulation_id
                    existing_agg.entity = agg_table.entity
                    existing_agg.variable_name = agg_table.variable_name
                    existing_agg.year = agg_table.year
                    existing_agg.filter_variable_name = agg_table.filter_variable_name
                    existing_agg.filter_variable_value = agg_table.filter_variable_value
                    existing_agg.filter_variable_leq = agg_table.filter_variable_leq
                    existing_agg.filter_variable_geq = agg_table.filter_variable_geq
                    existing_agg.aggregate_function = agg_table.aggregate_function
                    existing_agg.value = agg_table.value
                else:
                    # Create new aggregate
                    agg_table = AggregateTable.convert_from_model(aggregate, database)
                    database.session.add(agg_table)
            database.session.flush()

        return sim_table

    def convert_to_model(self, database: "Database" = None) -> Simulation:
        """Convert this SimulationTable instance to a Simulation instance.

        Args:
            database: The database instance for resolving foreign keys

        Returns:
            A Simulation instance
        """
        from sqlmodel import select

        from .model_version_table import ModelVersionTable
        from .policy_table import PolicyTable
        from .dataset_table import DatasetTable
        from .model_table import ModelTable
        from .dynamic_table import DynamicTable

        # Resolve all foreign keys
        policy = None
        dynamic = None
        dataset = None
        model = None
        model_version = None

        if database:
            if self.policy_id:
                policy_table = database.session.exec(
                    select(PolicyTable).where(PolicyTable.id == self.policy_id)
                ).first()
                if policy_table:
                    policy = policy_table.convert_to_model(database)

            if self.dynamic_id:
                try:
                    dynamic_table = database.session.exec(
                        select(DynamicTable).where(DynamicTable.id == self.dynamic_id)
                    ).first()
                    if dynamic_table:
                        dynamic = dynamic_table.convert_to_model(database)
                except:
                    # Dynamic table might not be defined yet
                    dynamic = database.get(Dynamic, id=self.dynamic_id)

            if self.dataset_id:
                dataset_table = database.session.exec(
                    select(DatasetTable).where(DatasetTable.id == self.dataset_id)
                ).first()
                if dataset_table:
                    dataset = dataset_table.convert_to_model(database)

            if self.model_id:
                model_table = database.session.exec(
                    select(ModelTable).where(ModelTable.id == self.model_id)
                ).first()
                if model_table:
                    model = model_table.convert_to_model(database)

            if self.model_version_id:
                version_table = database.session.exec(
                    select(ModelVersionTable).where(ModelVersionTable.id == self.model_version_id)
                ).first()
                if version_table:
                    model_version = version_table.convert_to_model(database)

        # Load aggregates
        aggregates = []
        if database:
            from .aggregate import AggregateTable
            from sqlmodel import select

            agg_tables = database.session.exec(
                select(AggregateTable).where(AggregateTable.simulation_id == self.id)
            ).all()

            for agg_table in agg_tables:
                # Don't pass database to avoid circular reference issues
                # The simulation reference will be set separately
                agg_model = agg_table.convert_to_model(None)
                aggregates.append(agg_model)

        return Simulation(
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            policy=policy,
            dynamic=dynamic,
            dataset=dataset,
            model=model,
            model_version=model_version,
            result=decompress_data(self.result) if self.result else None,
            aggregates=aggregates,
        )


simulation_table_link = TableLink(
    model_cls=Simulation,
    table_cls=SimulationTable,
)
