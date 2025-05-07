from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from sqlmodel import (
    Field,
    Session,
    SQLModel,
    create_engine,
    Relationship,
    select,
)
from enum import Enum
from pydantic import validator
from pathlib import Path


# Enums and Constants
class CountryCode(str, Enum):
    UK = "uk"
    US = "us"


class EntityType(str, Enum):
    ENTITY = "entity"  # Generic entity type


class BaseModel(SQLModel):
    """Base model with ID as primary key"""

    id: Optional[int] = Field(default=None, primary_key=True)


# Core policy models
class Country(BaseModel, table=True):
    """Country model representing supported jurisdictions"""

    code: str = Field(index=True, unique=True)  # 'uk', 'us'
    name: str  # 'United Kingdom', 'United States'

    # Relationships
    parameters: List["Parameter"] = Relationship(back_populates="country")
    reforms: List["Reform"] = Relationship(back_populates="country")
    entities: List["Entity"] = Relationship(back_populates="country")
    variables: List["Variable"] = Relationship(back_populates="country")
    simulation: List["Simulation"] = Relationship(back_populates="country")


class Reform(BaseModel, table=True):
    """A reform is a change to policy."""

    reform_id: str = Field(index=True)  # '35'
    name: str  # 'Set of parameter changes involving main tax rate'
    description: Optional[str] = None
    country_id: Optional[int] = Field(default=None, foreign_key="country.id")
    is_structural: bool = Field(
        default=False
    )  # True if the reform contains non-parametric changes

    # Relationships
    country: Optional[Country] = Relationship(back_populates="reforms")
    parameter_changes: List["ParameterChange"] = Relationship(
        back_populates="reform"
    )
    simulations: List["Simulation"] = Relationship(back_populates="reform")


class Parameter(BaseModel, table=True):
    """Tax or benefit parameter definition"""

    country_id: int = Field(foreign_key="country.id")
    parameter_name: str = Field(index=True)  # 'gov.tax.rate'

    # Relationships
    country: Country = Relationship(back_populates="parameters")
    parameter_changes: List["ParameterChange"] = Relationship(
        back_populates="parameter"
    )


class ParameterChange(BaseModel, table=True):
    """Change to a parameter in a reform"""

    parameter_id: int = Field(foreign_key="parameter.id")
    reform_id: int = Field(foreign_key="reform.id")
    value: str
    time_period: str  # '2025'

    # Relationships
    parameter: Parameter = Relationship(back_populates="parameter_changes")
    reform: Reform = Relationship(back_populates="parameter_changes")


# Entity and dataset models
class Entity(BaseModel, table=True):
    """Entity model representing individuals, households, or other units"""

    id: Optional[int] = Field(default=None, primary_key=True)
    country_id: int = Field(foreign_key="country.id")
    entity_type: str = Field(
        index=True
    )  # Type of entity (person, household, etc.)
    dataset_id: Optional[int] = Field(default=None, foreign_key="dataset.id")

    # Relationships
    country: Country = Relationship(back_populates="entities")
    dataset: Optional["Dataset"] = Relationship(back_populates="entities")
    variable_states: List["VariableState"] = Relationship(
        back_populates="entity"
    )


class VersionedDataset(BaseModel, table=True):
    """Dataset containing entity records"""

    name: str
    description: Optional[str] = None
    dataset_series_id: int = Field(foreign_key="datasetseries.id")

    datasets: List["Dataset"] = Relationship(
        back_populates="versioned_dataset"
    )
    dataset_series: "DatasetSeries" = Relationship(
        back_populates="versioned_datasets"
    )


class DatasetSeries(BaseModel, table=True):
    """Series of related datasets (e.g., annual survey data)"""

    name: str
    description: Optional[str] = None

    # Relationships
    versioned_datasets: List["VersionedDataset"] = Relationship(
        back_populates="dataset_series"
    )


class Dataset(BaseModel, table=True):
    """Tags linking datasets to series with versioning"""

    versioned_dataset_id: int = Field(
        foreign_key="versioneddataset.id", primary_key=True
    )
    dataset_series_id: int = Field(
        foreign_key="datasetseries.id", primary_key=True
    )
    version: str

    # Relationships
    entities: List[Entity] = Relationship(back_populates="dataset")
    versioned_dataset: VersionedDataset = Relationship(
        back_populates="datasets"
    )
    simulations: List["Simulation"] = Relationship(back_populates="dataset")


# Variable models
class Variable(BaseModel, table=True):
    """Definition of a specific variable (income, expenditure, etc.)"""

    country_id: int = Field(foreign_key="country.id")
    name: str = Field(index=True)
    description: Optional[str] = None

    # Relationships
    country: Country = Relationship(back_populates="variables")
    variable_states: List["VariableState"] = Relationship(
        back_populates="variable"
    )


class VariableState(BaseModel, table=True):
    """Specific value of a variable for an entity at a point in time"""

    variable_id: int = Field(foreign_key="variable.id")
    entity_id: int = Field(foreign_key="entity.id")
    time_period: str  # '2025'
    value: str  # '30000'
    simulation_id: Optional[int] = Field(
        default=None, foreign_key="simulation.id"
    )

    # Relationships
    variable: Variable = Relationship(back_populates="variable_states")
    entity: Entity = Relationship(back_populates="variable_states")
    simulation: Optional["Simulation"] = Relationship(
        back_populates="variable_states"
    )


class Simulation(BaseModel, table=True):
    """Record of a specific policy simulation"""

    country_id: int = Field(foreign_key="country.id")

    reform_id: Optional[int] = Field(default=None, foreign_key="reform.id")
    package_version: str
    dataset_id: int = Field(foreign_key="dataset.id")
    run_date: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    reform: Optional[Reform] = Relationship(back_populates="simulations")
    country: Country = Relationship(back_populates="simulations")
    dataset: Dataset = Relationship(back_populates="simulations")
    variable_states: List["VariableState"] = Relationship(
        back_populates="simulation"
    )


# Database management functions
def create_db_and_tables(connection_string="sqlite:///tax_policy.db"):
    """Create database and tables"""
    engine = create_engine(connection_string)
    SQLModel.metadata.create_all(engine)
    return engine
