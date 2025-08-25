"""SQLAlchemy models for PolicyEngine database."""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, 
    DateTime, JSON, ForeignKey, Enum, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
import importlib.metadata

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

def get_model_version(country: str) -> str:
    """Get the installed version of policyengine for a given country.
    
    Args:
        country: Country code (e.g., 'uk', 'us')
        
    Returns:
        Version string or None if package not found
    """
    try:
        package_name = f"policyengine-{country.lower()}"
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None

class SimulationStatus(enum.Enum):
    """Status of simulation processing."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User accounts for tracking who creates and modifies data."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True)
    
    # Authentication (optional - can integrate with external auth)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login = Column(DateTime, nullable=True)
    
    # API access (optional)
    api_key = Column(String, nullable=True, unique=True, index=True)
    api_key_created_at = Column(DateTime, nullable=True)
    
    # Additional metadata
    metadata_json = Column(JSON, nullable=True)  # For storing additional user data


# Metadata models only - actual data stored in .h5 files

class SimulationMetadata(Base):
    """Metadata for simulation stored in .h5 file. e.g. 'current law, EFRS 2023/24 based, 2026'"""
    __tablename__ = "simulations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    country = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    
    # Storage information
    file_size_mb = Column(Float, nullable=True)
    
    # Scenario information
    dataset = Column(String, nullable=False)  # e.g., "frs_2023_24"
    scenario = Column(String, nullable=False)  # e.g., "baseline"
    model_version = Column(String, nullable=True)  # e.g., "0.5.2"

    # Processing metadata
    status = Column(Enum(SimulationStatus), default=SimulationStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    # Optional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags for filtering
    created_by = Column(String, ForeignKey("users.id"), nullable=True)  # User/system that created it


class DatasetMetadata(Base):
    """Metadata for source datasets. e.g. 'EFRS 2023/24'"""
    __tablename__ = "datasets"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True, index=True)
    country = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    
    # Dataset characteristics
    source = Column(String, nullable=True)  # "FRS", "CPS", etc.
    version = Column(String, nullable=True)
    model_version = Column(String, nullable=True)  # e.g., "0.5.2"
    
    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)


class ScenarioMetadata(Base):
    """Modifications made to baseline simulation behaviour."""
    __tablename__ = "scenarios"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False, index=True)
    model_version = Column(String, nullable=True)  # e.g., "0.5.2"
    
    # Metadata
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    parameter_changes = relationship("ParameterChangeMetadata", back_populates="scenario", cascade="all, delete-orphan")
    
    # Unique constraint on (name, country) - same name allowed across countries
    __table_args__ = (
        UniqueConstraint('name', 'country', name='_scenario_name_country_uc'),
    )


class ParameterMetadata(Base):
    """Registry of all parameters that can be modified."""
    __tablename__ = "parameters"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)  # e.g., "gov.basic_rate"
    country = Column(String, nullable=False, index=True)
    parent_id = Column(String, ForeignKey("parameters.id"), nullable=True)

    # Parameter metadata
    label = Column(String, nullable=True)  # Human-readable name
    description = Column(Text, nullable=True)
    unit = Column(String, nullable=True)  # e.g., "GBP", "percent", "boolean"
    data_type = Column(String, nullable=False)  # "float", "int", "bool", "string"
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    changes = relationship("ParameterChangeMetadata", back_populates="parameter", cascade="all, delete-orphan")


class ParameterChangeMetadata(Base):
    """Individual parameter change within a scenario."""
    __tablename__ = "parameter_changes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Foreign keys
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False, index=True)
    parameter_id = Column(String, ForeignKey("parameters.id"), nullable=False, index=True)
    
    # Time period for this change
    start_date = Column(DateTime, nullable=False, index=True)  # When this change takes effect
    end_date = Column(DateTime, nullable=True, index=True)  # When this change expires (null = indefinite)
    
    # The actual change
    value = Column(JSON, nullable=False)  # JSON to handle different data types
    
    # Ordering within scenario (for applying changes in sequence)
    order_index = Column(Integer, nullable=False, default=0)
    
    # Metadata
    model_version = Column(String, nullable=True)  # e.g., "0.5.2"
    description = Column(Text, nullable=True)  # Optional description of this specific change
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    scenario = relationship("ScenarioMetadata", back_populates="parameter_changes")
    parameter = relationship("ParameterMetadata", back_populates="changes")
