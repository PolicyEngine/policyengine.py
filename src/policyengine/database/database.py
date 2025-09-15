from pydantic import BaseModel
from sqlmodel import SQLModel, Field, JSON, Column, Session, select, MetaData
from typing import Optional, List, Any, Callable
from datetime import datetime
from uuid import uuid4
from policyengine.models import Model, Policy, Dynamic, Dataset, Simulation, Parameter, ParameterValue
import pickle
from .link import TableLink
from .model import model_table_link, model_version_table_link

class PolicyTable(SQLModel, table=True):
    __tablename__ = "policies"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    parameter_value_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class DynamicTable(SQLModel, table=True):
    __tablename__ = "dynamics"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    parameter_value_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)



class ParameterTable(SQLModel, table=True):
    __tablename__ = "parameters"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    description: str = Field(nullable=False)
    data_type: str = Field(nullable=False)
    model_id: Optional[str] = Field(default=None)

class ParameterValueTable(SQLModel, table=True):
    __tablename__ = "parameter_values"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    parameter_id: str = Field(nullable=False)
    value: float = Field(nullable=False)
    start_date: datetime = Field(nullable=False)
    end_date: Optional[datetime] = Field(default=None)

class VersionedDatasetTable(SQLModel, table=True):
    __tablename__ = "versioned_datasets"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: str = Field(nullable=False)
    model_id: Optional[str] = Field(default=None, foreign_key="models.id")

class DatasetTable(SQLModel, table=True):
    __tablename__ = "datasets"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: str = Field(nullable=False)
    version: Optional[str] = Field(default=None)
    versioned_dataset_id: Optional[str] = Field(default=None, foreign_key="versioned_datasets.id")
    year: Optional[int] = Field(default=None)
    data: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    model_id: Optional[str] = Field(default=None, foreign_key="models.id")

class SimulationTable(SQLModel, table=True):
    __tablename__ = "simulations"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    policy_id: Optional[str] = Field(default=None, foreign_key="policies.id")
    dynamic_id: Optional[str] = Field(default=None, foreign_key="dynamics.id")
    dataset_id: str = Field(foreign_key="datasets.id")
    model_version_id: Optional[str] = Field(default=None, foreign_key="model_versions.id")
    result: Optional[Any] = Field(default=None, sa_column=Column(JSON))

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
        table_link = next((link for link in self._model_table_links if link.model_cls == model_cls), None)
        if table_link is not None:
            table_link.get(self, **kwargs)

    def set(self, object: Any):
        table_link = next((link for link in self._model_table_links if link.model_cls == type(object)), None)
        if table_link is not None:
            table_link.set(self, object)

# Now, define the table links

