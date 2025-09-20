from typing import Any

from sqlmodel import Session, SQLModel

from .aggregate import aggregate_table_link
from .baseline_parameter_value_table import baseline_parameter_value_table_link
from .baseline_variable_table import baseline_variable_table_link
from .dataset_table import dataset_table_link
from .dynamic_table import dynamic_table_link
from .link import TableLink

# Import all table links
from .model_table import model_table_link
from .model_version_table import model_version_table_link
from .parameter_table import parameter_table_link
from .parameter_value_table import parameter_value_table_link
from .policy_table import policy_table_link
from .report_element_table import report_element_table_link
from .report_table import report_table_link
from .simulation_table import simulation_table_link
from .user_table import user_table_link
from .versioned_dataset_table import versioned_dataset_table_link


class Database:
    url: str

    _model_table_links: list[TableLink] = []

    def __init__(self, url: str):
        self.url = url
        self.engine = self._create_engine()
        self.session = Session(self.engine)

        for link in [
            model_table_link,
            model_version_table_link,
            dataset_table_link,
            versioned_dataset_table_link,
            policy_table_link,
            dynamic_table_link,
            parameter_table_link,
            parameter_value_table_link,
            baseline_parameter_value_table_link,
            baseline_variable_table_link,
            simulation_table_link,
            aggregate_table_link,
            user_table_link,
            report_table_link,
            report_element_table_link,
        ]:
            self.register_table(link)

    def _create_engine(self):
        from sqlmodel import create_engine

        return create_engine(self.url, echo=False)

    def create_tables(self):
        """Create all database tables."""
        SQLModel.metadata.create_all(self.engine)

    def drop_tables(self):
        """Drop all database tables."""
        SQLModel.metadata.drop_all(self.engine)

    def reset(self):
        """Drop and recreate all tables."""
        self.drop_tables()
        self.create_tables()

    def __enter__(self):
        """Context manager entry - creates a session."""
        self.session = Session(self.engine)
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes the session."""
        if exc_type:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()

    def register_table(self, link: TableLink):
        self._model_table_links.append(link)
        # Create the table if not exists
        link.table_cls.metadata.create_all(self.engine)

    def get(self, model_cls: type, **kwargs):
        table_link = next(
            (
                link
                for link in self._model_table_links
                if link.model_cls == model_cls
            ),
            None,
        )
        if table_link is not None:
            return table_link.get(self, **kwargs)

    def set(self, object: Any, commit: bool = True):
        table_link = next(
            (
                link
                for link in self._model_table_links
                if link.model_cls is type(object)
            ),
            None,
        )
        if table_link is not None:
            table_link.set(self, object, commit=commit)

    def register_model_version(self, model_version):
        """Register a model version with its model and seed objects.
        This replaces all existing parameters, baseline parameter values,
        and baseline variables for this model version."""
        # Add or update the model directly to avoid conflicts
        from policyengine.utils.compress import compress_data

        from .baseline_parameter_value_table import BaselineParameterValueTable
        from .baseline_variable_table import BaselineVariableTable
        from .model_table import ModelTable
        from .model_version_table import ModelVersionTable
        from .parameter_table import ParameterTable

        existing_model = (
            self.session.query(ModelTable)
            .filter(ModelTable.id == model_version.model.id)
            .first()
        )
        if not existing_model:
            model_table = ModelTable(
                id=model_version.model.id,
                name=model_version.model.name,
                description=model_version.model.description,
                simulation_function=(
                    lambda m: compress_data(m.simulation_function)
                )(model_version.model),
            )
            self.session.add(model_table)
            self.session.flush()

        # Add or update the model version
        existing_version = (
            self.session.query(ModelVersionTable)
            .filter(ModelVersionTable.id == model_version.id)
            .first()
        )
        if not existing_version:
            version_table = ModelVersionTable(
                id=model_version.id,
                model_id=model_version.model.id,
                version=model_version.version,
                description=model_version.description,
                created_at=model_version.created_at,
            )
            self.session.add(version_table)
            self.session.flush()

        # Get seed objects from the model
        seed_objects = model_version.model.create_seed_objects(model_version)

        # Delete ALL existing seed data for this model (not just this version)
        # This ensures we start fresh with the new version's data
        # Order matters due to foreign key constraints

        # First delete baseline parameter values (they reference parameters)
        self.session.query(BaselineParameterValueTable).filter(
            BaselineParameterValueTable.model_id == model_version.model.id
        ).delete()

        # Then delete baseline variables for this model
        self.session.query(BaselineVariableTable).filter(
            BaselineVariableTable.model_id == model_version.model.id
        ).delete()

        # Finally delete all parameters for this model
        self.session.query(ParameterTable).filter(
            ParameterTable.model_id == model_version.model.id
        ).delete()

        self.session.commit()

        # Add all parameters first
        for parameter in seed_objects.parameters:
            # We need to add directly to session to avoid the autoflush issue
            from .parameter_table import ParameterTable

            param_table = ParameterTable(
                id=parameter.id,
                model_id=parameter.model.id,  # Now required as part of composite key
                description=parameter.description,
                data_type=parameter.data_type.__name__
                if parameter.data_type
                else None,
            )
            self.session.add(param_table)

        # Flush parameters to database so they exist for foreign key constraints
        self.session.flush()

        # Add all baseline parameter values
        for baseline_param_value in seed_objects.baseline_parameter_values:
            import math
            from uuid import uuid4

            from .baseline_parameter_value_table import (
                BaselineParameterValueTable,
            )

            # Handle special float values that JSON doesn't support
            value = baseline_param_value.value
            if isinstance(value, float):
                if math.isinf(value):
                    value = "Infinity" if value > 0 else "-Infinity"
                elif math.isnan(value):
                    value = "NaN"

            bpv_table = BaselineParameterValueTable(
                id=str(uuid4()),
                parameter_id=baseline_param_value.parameter.id,
                model_id=baseline_param_value.parameter.model.id,  # Add model_id
                model_version_id=baseline_param_value.model_version.id,
                value=value,
                start_date=baseline_param_value.start_date,
                end_date=baseline_param_value.end_date,
            )
            self.session.add(bpv_table)

        # Add all baseline variables
        for baseline_variable in seed_objects.baseline_variables:
            from .baseline_variable_table import BaselineVariableTable

            bv_table = BaselineVariableTable(
                id=baseline_variable.id,
                model_id=baseline_variable.model_version.model.id,  # Add model_id
                model_version_id=baseline_variable.model_version.id,
                entity=baseline_variable.entity,
                label=baseline_variable.label,
                description=baseline_variable.description,
                data_type=(lambda bv: compress_data(bv.data_type))(
                    baseline_variable
                )
                if baseline_variable.data_type
                else None,
            )
            self.session.add(bv_table)

        # Commit everything at once
        self.session.commit()
