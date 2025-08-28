"""Pydantic models for PolicyEngine."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import pandas as pd


class SimulationStatus(str, Enum):
    """Status of simulation processing."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Dataset(BaseModel):
    """Metadata for data files. Overridden by country versions."""
    name: str
    
    # Dataset characteristics
    source_dataset: Optional["Dataset"] = None
    version: Optional[str] = None
    
    # Local storage
    local_path: Optional[str] = None
    
    # Google Cloud Storage
    gcs_bucket: Optional[str] = None
    gcs_path: Optional[str] = None
    
    # HuggingFace
    huggingface_repo: Optional[str] = None
    huggingface_path: Optional[str] = None
    
    # File metadata
    file_size_mb: Optional[float] = None

    def __init__(self):
        self.load()

    def load(self):
        """Load dataset from local path."""
        raise NotImplementedError("Dataset load method must be implemented in country-specific subclass.")

    def save(self, path: str) -> None:
        """Save dataset to local path."""
        raise NotImplementedError("Dataset save method must be implemented in country-specific subclass.")


class Rules(BaseModel):
    """Modifications made to baseline tax-benefit rules."""
    name: str

    # Parent rules reference
    parent_rules: Optional["Rules"] = None
    
    # Metadata
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None # Should automatically be current datetime

    _parameter_changes: Optional[dict] = None
    _simulation_modifier: Optional[Any] = None

class Dynamics(BaseModel):
    """Modifications made to baseline tax-benefit dynamics."""
    name: str

    # Parent dynamics reference
    parent_dynamics: Optional["Dynamics"] = None
    
    # Metadata
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None # Should automatically be current datetime

    _parameter_changes: Optional[dict] = None
    _simulation_modifier: Optional[Any] = None


class Simulation(BaseModel):
    """Metadata for simulation, stored in .h5 file. Overridden by country versions."""
    # Foreign key references
    data: Dataset
    rules: Rules
    dynamics: Dynamics
    output_dataset: Optional[Dataset] = None
    model_version: Optional[str] = None
    
    # Processing metadata
    status: SimulationStatus = SimulationStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def run(self) -> Dataset:
        """Run the simulation."""
        raise NotImplementedError("Simulation run method must be implemented in country-specific subclass.")

class ReportElementDataItem(BaseModel):
    report_element: "ReportElement"

class ReportElement(BaseModel):
    """An element of a report, which may include tables, charts, and other visualizations."""
    name: str
    description: Optional[str] = None
    data_items: List[ReportElementDataItem] = []
    report: "Report"

    @property
    def data(self) -> pd.DataFrame:
        # Get pydantic fields from reportelementdataitem-inheriting classes
        data = []
        for item in self.data_items:
            data.append(item.model_dump())
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
    rules: "Rules"
    dynamics: "Dynamics"
    parameter: "Parameter"
    
    # Time period for this change
    start_date: datetime
    end_date: Optional[datetime] = None
    
    # The actual change
    value: Any  # JSON-serializable value
