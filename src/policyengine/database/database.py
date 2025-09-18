from sqlmodel import SQLModel, Session
from typing import Any
from .link import TableLink

# Import all table links
from .model_table import model_table_link
from .model_version_table import model_version_table_link
from .dataset_table import dataset_table_link
from .versioned_dataset_table import versioned_dataset_table_link
from .policy_table import policy_table_link
from .dynamic_table import dynamic_table_link
from .parameter_table import parameter_table_link
from .parameter_value_table import parameter_value_table_link
from .simulation_table import simulation_table_link
from .aggregate import aggregate_table_link


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
            simulation_table_link,
            aggregate_table_link,
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
            table_link.get(self, **kwargs)

    def set(self, object: Any):
        table_link = next(
            (
                link
                for link in self._model_table_links
                if link.model_cls == type(object)
            ),
            None,
        )
        if table_link is not None:
            table_link.set(self, object)
