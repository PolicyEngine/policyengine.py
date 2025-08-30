from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
import uuid
from typing import Optional

class Dataset(SQLModel, table=True):
    __tablename__ = "datasets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    source_dataset_id: str = Field(default=None, foreign_key="datasets.id")
    version: str
    data: Optional[str] = None  # Could be a path or JSON blob

class Policy(SQLModel, table=True):
    __tablename__ = "policies"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    parent_id: str = Field(default=None, foreign_key="policies.id")
    description: str
    simulation_modifier: str

class Dynamics(SQLModel, table=True):
    __tablename__ = "dynamics"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    parent_id: str = Field(default=None, foreign_key="dynamics.id")
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Simulation(SQLModel, table=True):
    __tablename__ = "simulations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    data_id: str = Field(default=None, foreign_key="datasets.id")
    policy_id: str = Field(default=None, foreign_key="policies.id")
    dynamics_id: str = Field(default=None, foreign_key="dynamics.id")
    output_dataset_id: str = Field(default=None, foreign_key="datasets.id")
    model_version: str
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReportElementDataItem(SQLModel, table=True):
    __tablename__ = "report_element_data_items"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    report_element_id: str = Field(default=None, foreign_key="report_elements.id")

class ReportElement(SQLModel, table=True):
    __tablename__ = "report_elements"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    description: str
    report_id: str = Field(default=None, foreign_key="reports.id")
    status: str = Field(default="pending")

class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    description: str

class Variable(SQLModel, table=True):
    __tablename__ = "variables"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    label: str
    description: str
    unit: str
    value_type: str
    entity: str
    definition_period: str

class Parameter(SQLModel, table=True):
    __tablename__ = "parameters"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    parent_id: str = Field(default=None, foreign_key="parameters.id")
    label: str
    description: str
    unit: str
    data_type: str

class ParameterValue(SQLModel, table=True):
    __tablename__ = "parameter_values"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    parameter_id: str = Field(default=None, foreign_key="parameters.id")
    value: str
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_date: Optional[datetime] = Field(default=None)
    policy_id: str = Field(default=None, foreign_key="policies.id")
    dynamics_id: str = Field(default=None, foreign_key="dynamics.id")