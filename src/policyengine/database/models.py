"""SQLAlchemy models for PolicyEngine database."""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, 
    DateTime, JSON, ForeignKey, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class SimulationStatus(enum.Enum):
    """Status of simulation processing."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Metadata models only - actual data stored in .h5 files

class SimulationMetadata(Base):
    """Metadata for simulation stored in .h5 file. e.g. 'current law, EFRS 2023/24 based, 2026'"""
    __tablename__ = "simulations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    
    # Storage information
    file_size_mb = Column(Float, nullable=True)
    
    # Scenario information
    dataset = Column(String, nullable=False)  # e.g., "frs_2023_24"
    scenario = Column(String, nullable=False)  # e.g., "baseline"

    # Processing metadata
    status = Column(Enum(SimulationStatus), default=SimulationStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    # Optional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags for filtering
    created_by = Column(String, nullable=True)  # User/system that created it


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
    
    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Scenario(Base):
    """Modifications made to baseline simulation behaviour."""
    __tablename__ = "scenarios"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True, index=True)
    country = Column(String, nullable=False, index=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, nullable=True)
