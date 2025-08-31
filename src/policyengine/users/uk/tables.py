from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
import uuid
from typing import Optional
from policyengine.models import OperationStatus
from policyengine.utils.dataframe_storage import serialise_dataframe_dict
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
import uuid
from typing import Optional, List
from policyengine.models import OperationStatus, Dataset, Policy, Dynamics, Simulation
from policyengine.users.uk.models import AggregateChange, AggregateChanges

class PolicyDB(SQLModel, table=True):
    __tablename__ = "policies"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    parent_id: Optional[str] = Field(default=None, foreign_key="policies.id")

class DynamicsDB(SQLModel, table=True):
    __tablename__ = "dynamics"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    parent_id: Optional[str] = Field(default=None, foreign_key="dynamics.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReportElementDataItemDB(SQLModel, table=True):
    __tablename__ = "report_element_data_items"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    report_element_id: str = Field(default=None, foreign_key="report_elements.id")

class ReportElementDB(SQLModel, table=True):
    __tablename__ = "report_elements"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    report_id: str = Field(default=None, foreign_key="reports.id")
    status: str = Field(default="pending")

class ReportDB(SQLModel, table=True):
    __tablename__ = "reports"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

class VariableDB(SQLModel, table=True):
    __tablename__ = "variables"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

class ParameterDB(SQLModel, table=True):
    __tablename__ = "parameters"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    parent_id: str = Field(default=None, foreign_key="parameters.id")

class ParameterValueDB(SQLModel, table=True):
    __tablename__ = "parameter_values"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    parameter_id: str = Field(default=None, foreign_key="parameters.id")
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_date: Optional[datetime] = Field(default=None)
    policy_id: Optional[str] = Field(default=None, foreign_key="policies.id")
    dynamics_id: Optional[str] = Field(default=None, foreign_key="dynamics.id")

class DatasetDB(SQLModel, table=True, extend_existing=True):
    __tablename__ = "datasets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    source_dataset_id: str = Field(default=None, foreign_key="datasets.id")
    data: Optional[str] = None  # Could be a path or JSON blob

class SimulationDB(SQLModel, table=True, extend_existing=True):
    __tablename__ = "simulations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    data_id: Optional[str] = Field(default=None, foreign_key="datasets.id")
    policy_id: Optional[str] = Field(default=None, foreign_key="policies.id")
    dynamics_id: Optional[str] = Field(default=None, foreign_key="dynamics.id")
    output_dataset_id: Optional[str] = Field(default=None, foreign_key="datasets.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AggregateChangeDB(SQLModel, table=True):
    __tablename__ = "aggregate_changes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    report_element_id: str = Field(default=None, foreign_key="aggregate_changes.id")

class AggregateChangeReportElementDB(SQLModel, table=True):
    __tablename__ = "aggregate_change_report_elements"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)