"""Pydantic models for PolicyEngine."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import pandas as pd


class OperationStatus(str, Enum):
    """Status of simulation processing."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Dataset(BaseModel):
    """A dataset used or created by a simulation."""

    name: Optional[str] = None
    # Dataset characteristics
    source_dataset: Optional["Dataset"] = None
    version: Optional[str] = None


class Policy(BaseModel):
    """Modifications made to baseline tax-benefit rules."""

    name: Optional[str] = None

    # Parent policy reference
    parent: Optional["Policy"] = None

    # Metadata
    description: Optional[str] = None

    parameter_values: Optional[List["ParameterValue"]] = None
    simulation_modifier: Optional[Any] = None


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


class Simulation(BaseModel):
    """Metadata for simulation, stored in .h5 file. Overridden by country versions."""

    # Foreign key references
    data: Dataset
    policy: Policy
    dynamics: Dynamics
    output_dataset: Optional[Dataset] = None
    model_version: Optional[str] = None

    # Processing metadata
    status: OperationStatus = OperationStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def run(self) -> Dataset:
        """Run the simulation."""
        raise NotImplementedError(
            "Simulation run method must be implemented in country-specific subclass."
        )


class ReportElementDataItem(BaseModel):
    report_element: "ReportElement"


class ReportElement(BaseModel):
    """An element of a report, which may include tables, charts, and other visualizations."""

    name: Optional[str] = None
    description: Optional[str] = None
    data_items: List[ReportElementDataItem] = []
    report: Optional["Report"] = None
    status: OperationStatus = OperationStatus.PENDING

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


class Report(BaseModel):
    """A report generated from a simulation."""

    name: str
    description: Optional[str] = None
    elements: List[ReportElement] = []


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


class Parameter(BaseModel):
    """Policy parameter of the country package model."""

    name: str
    country: str
    parent: Optional["Parameter"] = None  # For hierarchical parameters

    # Parameter metadata
    label: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    data_type: str  # "float", "int", "bool", "string"


class ParameterValue(BaseModel):
    """Individual parameter value for some point in time."""

    # Foreign keys
    policy: Optional["Policy"] = None
    dynamics: Optional["Dynamics"] = None
    parameter: Parameter

    # Time period for this change
    start_date: datetime
    end_date: Optional[datetime] = None

    # The actual change
    value: Any  # JSON-serializable value