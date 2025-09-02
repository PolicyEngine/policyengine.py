"""Pydantic models for PolicyEngine."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field
import uuid
from policyengine.utils.dataframe_storage import deserialise_dataframe_dict
from enum import Enum
import pandas as pd


class OperationStatus(str, Enum):
    """Status of simulation processing."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class DatasetType(str, Enum):
    """Data types for dataset fields."""
    UK = "uk"
    US = "us"


class Dataset(BaseModel):
    """A dataset used or created by a simulation."""

    name: Optional[str] = None
    # Dataset characteristics
    source_dataset: Optional["Dataset"] = None
    version: Optional[str] = None
    data: Optional[Any] = None
    dataset_type: DatasetType


class Policy(BaseModel):
    """Modifications made to baseline tax-benefit rules."""

    name: Optional[str] = None

    # Metadata
    description: Optional[str] = None

    parameter_values: Optional[List["ParameterValue"]] = None
    simulation_modifier: Optional[Any] = None
    country: Optional[str] = None


class Dynamics(BaseModel):
    """Modifications made to baseline tax-benefit dynamics."""

    name: Optional[str] = None

    # Parent dynamics reference
    parent_dynamics: Optional["Dynamics"] = None

    # Metadata
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None  # Should automatically be current datetime

    parameter_values: Optional[List["ParameterValue"]] = None
    simulation_modifier: Optional[Any] = None
    country: Optional[str] = None


class Simulation(BaseModel):
    """Metadata for simulation. Re-implemented by country versions."""

    # Foreign key references
    dataset: Dataset
    policy: Policy
    dynamics: Dynamics
    output_data: Optional[Any] = None
    model_version: Optional[str] = None
    country: str

    # Processing metadata
    status: OperationStatus = OperationStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def run(self) -> Dataset:
        """Run the simulation."""
        if self.country == "uk":
            from policyengine.countries.uk.simulation import run_uk_simulation
            return run_uk_simulation(self)


class ReportElementDataItem(BaseModel):
    report_element: "ReportElement"



class ReportElement(BaseModel):
    """An element of a report, which may include tables, charts, and other visualizations."""

    name: Optional[str] = None
    description: Optional[str] = None
    data_items: List[ReportElementDataItem] = []
    report: Optional["Report"] = None
    status: OperationStatus = OperationStatus.PENDING
    country: Optional[str] = None
    data_item_type: Optional[str] = None

    @property
    def data(self) -> pd.DataFrame:
        # Get pydantic fields from reportelementdataitem-inheriting classes
        data = []
        for item in self.data_items:
            non_inherited_fields = (
                type(item).model_fields.keys()
                - ReportElementDataItem.model_fields.keys()
            )
            data.append({key: getattr(item, key) for key in non_inherited_fields})
        return pd.DataFrame(data)
    
    def run(self):
        raise NotImplementedError("ReportElement run method must be implemented in country-specific subclass.")


class Report(BaseModel):
    """A report generated from a simulation."""

    name: str
    description: Optional[str] = None
    elements: List[ReportElement] = []
    country: Optional[str] = None


class Variable(BaseModel):
    """PolicyEngine variable concept- an attribute of an entity."""

    name: str

    # Variable metadata
    label: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    value_type: str  # "float", "int", "bool", "string", "enum"
    entity: str  # "person", "household", "tax_unit", etc.
    definition_period: Optional[str] = None  # "year", "month", "eternity"
    country: Optional[str] = None


class Parameter(BaseModel):
    """Policy parameter of the country package model."""

    name: str
    parent: Optional["Parameter"] = None  # For hierarchical parameters

    # Parameter metadata
    label: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    data_type: type  # "float", "int", "bool", "string"
    country: Optional[str] = None


class ParameterValue(BaseModel):
    """Individual parameter value for some point in time."""

    # Foreign keys
    policy: Optional["Policy"] = None
    dynamics: Optional["Dynamics"] = None
    parameter: Parameter
    model_version: str

    # Time period for this change
    start_date: datetime
    end_date: Optional[datetime] = None

    # The actual change
    value: Any  # JSON-serializable value
    country: Optional[str] = None
