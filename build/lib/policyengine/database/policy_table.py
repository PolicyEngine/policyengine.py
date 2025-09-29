from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlmodel import Field, SQLModel

from policyengine.models import Policy
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class PolicyTable(SQLModel, table=True):
    __tablename__ = "policies"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    simulation_modifier: bytes | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def convert_from_model(cls, model: Policy, database: "Database" = None) -> "PolicyTable":
        """Convert a Policy instance to a PolicyTable instance.

        Args:
            model: The Policy instance to convert
            database: The database instance for persisting nested objects

        Returns:
            A PolicyTable instance
        """
        policy_table = cls(
            id=model.id,
            name=model.name,
            description=model.description,
            simulation_modifier=compress_data(model.simulation_modifier) if model.simulation_modifier else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

        # Handle nested parameter values if database is provided
        if database and model.parameter_values:
            from .parameter_value_table import ParameterValueTable
            from sqlmodel import select

            # First ensure the policy table is saved to the database
            # This is necessary so the foreign key constraint is satisfied
            # Check if it already exists
            existing_policy = database.session.exec(
                select(PolicyTable).where(PolicyTable.id == model.id)
            ).first()

            if not existing_policy:
                database.session.add(policy_table)
                database.session.flush()

            # Track which parameter value IDs we want to keep
            desired_pv_ids = {pv.id for pv in model.parameter_values}

            # Delete only parameter values linked to this policy that are NOT in the new list
            existing_pvs = database.session.exec(
                select(ParameterValueTable).where(ParameterValueTable.policy_id == model.id)
            ).all()
            for pv in existing_pvs:
                if pv.id not in desired_pv_ids:
                    database.session.delete(pv)

            # Now save/update the parameter values
            for param_value in model.parameter_values:
                # Check if this parameter value already exists in the database
                existing_pv = database.session.exec(
                    select(ParameterValueTable).where(ParameterValueTable.id == param_value.id)
                ).first()

                if existing_pv:
                    # Update existing parameter value
                    pv_table = ParameterValueTable.convert_from_model(param_value, database)
                    existing_pv.parameter_id = pv_table.parameter_id
                    existing_pv.model_id = pv_table.model_id
                    existing_pv.policy_id = model.id
                    existing_pv.value = pv_table.value
                    existing_pv.start_date = pv_table.start_date
                    existing_pv.end_date = pv_table.end_date
                else:
                    # Create new parameter value
                    pv_table = ParameterValueTable.convert_from_model(param_value, database)
                    pv_table.policy_id = model.id  # Link to this policy
                    database.session.add(pv_table)
            database.session.flush()

        return policy_table

    def convert_to_model(self, database: "Database" = None) -> Policy:
        """Convert this PolicyTable instance to a Policy instance.

        Args:
            database: The database instance for loading nested objects

        Returns:
            A Policy instance
        """
        # Load nested parameter values if database is provided
        parameter_values = []
        if database:
            from .parameter_value_table import ParameterValueTable
            from sqlmodel import select

            # Query for all parameter values linked to this policy
            pv_tables = database.session.exec(
                select(ParameterValueTable).where(ParameterValueTable.policy_id == self.id)
            ).all()

            # Convert each one to a model
            for pv_table in pv_tables:
                parameter_values.append(pv_table.convert_to_model(database))

        return Policy(
            id=self.id,
            name=self.name,
            description=self.description,
            parameter_values=parameter_values,
            simulation_modifier=decompress_data(self.simulation_modifier) if self.simulation_modifier else None,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


policy_table_link = TableLink(
    model_cls=Policy,
    table_cls=PolicyTable,
)
