from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
import uuid
from typing import Optional
from policyengine.models import OperationStatus
from policyengine.utils.dataframe_storage import (
    serialise_dataframe_dict,
    deserialise_dataframe_dict,
)
from policyengine.users.uk.models import UKSingleYearDataset, Dataset
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
import uuid
from typing import Optional, List
from policyengine.models import OperationStatus, Policy, Dynamics, Simulation
from policyengine.users.uk.models import AggregateChange, AggregateChangeReportElement


class PolicyDB(SQLModel, table=True):
    __tablename__ = "policies"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: Optional[str] = None
    description: Optional[str] = None

    parameter_values: List["ParameterValueDB"] = Relationship(back_populates="policy")


class DynamicsDB(SQLModel, table=True):
    __tablename__ = "dynamics"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: Optional[str] = None

    parameter_values: List["ParameterValueDB"] = Relationship(back_populates="dynamics")


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
    name: str

    # Variable metadata
    label: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    value_type: str  # "float", "int", "bool", "string", "enum"
    entity: str  # "person", "household", "tax_unit", etc.
    definition_period: Optional[str] = None  # "year", "month", "eternity"


class ParameterDB(SQLModel, table=True):
    __tablename__ = "parameters"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    data_type: Optional[str] = None
    parent_id: Optional[str] = Field(default=None, foreign_key="parameters.id")


class ParameterValueDB(SQLModel, table=True):
    __tablename__ = "parameter_values"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    parameter_id: str = Field(default=None, foreign_key="parameters.id")
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_date: Optional[datetime] = Field(default=None)
    value: Optional[str] = Field(default=None)
    policy_id: Optional[str] = Field(default=None, foreign_key="policies.id")
    policy: Optional["PolicyDB"] = Relationship(back_populates="parameter_values")
    dynamics_id: Optional[str] = Field(default=None, foreign_key="dynamics.id")
    dynamics: Optional["DynamicsDB"] = Relationship(back_populates="parameter_values")


class DatasetDB(SQLModel, table=True):
    __tablename__ = "datasets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    source_dataset_id: Optional[str] = Field(default=None, foreign_key="datasets.id")
    data: Optional[bytes] = None  # Could be a path or JSON blob
    name: Optional[str] = None
    year: Optional[int] = None

    def to_model(self) -> Dataset:
        deserialised_data = deserialise_dataframe_dict(self.data)
        single_year_data = UKSingleYearDataset(
            person=deserialised_data.get("person"),
            benunit=deserialised_data.get("benunit"),
            household=deserialised_data.get("household"),
        )
        return Dataset(
            name=self.name,
            data=single_year_data,
            year=self.year,
        )


class SimulationDB(SQLModel, table=True):
    __tablename__ = "simulations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    dataset_id: str = Field(default=None, foreign_key="datasets.id")
    dataset: DatasetDB = Relationship()
    policy_id: str = Field(default=None, foreign_key="policies.id")
    policy: PolicyDB = Relationship()
    dynamics_id: str = Field(default=None, foreign_key="dynamics.id")
    dynamics: DynamicsDB = Relationship()
    output_data: Optional[bytes] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    year: Optional[int] = None

    def __init__(self, **kwargs):
        output_data: Dataset = kwargs.get("output_data")
        if output_data is not None and not isinstance(output_data, bytes):
            encoded = serialise_dataframe_dict(
                {
                    "person": output_data.data.person,
                    "benunit": output_data.data.benunit,
                    "household": output_data.data.household,
                }
            )
            kwargs["output_data"] = encoded
        super().__init__(**kwargs)


class AggregateChangeDB(SQLModel, table=True):
    __tablename__ = "aggregate_changes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    report_element_id: str = Field(default=None, foreign_key="aggregate_changes.id")


class AggregateChangeReportElementDB(SQLModel, table=True):
    __tablename__ = "aggregate_change_report_elements"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
