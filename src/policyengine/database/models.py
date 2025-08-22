"""SQLAlchemy models for PolicyEngine database."""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, 
    DateTime, JSON, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


# Core entity models

class ScenarioDataModel(Base):
    """Scenario table model."""
    __tablename__ = "scenarios"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    country = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    parameter_changes = relationship("ParameterChangeDataModel", back_populates="scenario", cascade="all, delete-orphan")
    simulations = relationship("SimulationDataModel", back_populates="scenario", cascade="all, delete-orphan")


class ParameterChangeDataModel(Base):
    """Parameter change table model."""
    __tablename__ = "parameter_changes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)
    country = Column(String, nullable=False, index=True)
    parameter_path = Column(String, nullable=False)
    period = Column(String, nullable=True)  # e.g., "2024", "2024-01", "2024-Q1"
    value = Column(JSON, nullable=False)  # Can store various value types
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    scenario = relationship("ScenarioDataModel", back_populates="parameter_changes")


class PopulationDataModel(Base):
    """Population table model."""
    __tablename__ = "populations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    country = Column(String, nullable=False, index=True)
    source_dataset_id = Column(String, ForeignKey("source_datasets.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    source_dataset = relationship("SourceDatasetDataModel", back_populates="populations")
    simulations = relationship("SimulationDataModel", back_populates="population")


class SourceDatasetDataModel(Base):
    """Source dataset table model."""
    __tablename__ = "source_datasets"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    year = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    populations = relationship("PopulationDataModel", back_populates="source_dataset")


class SimulationDataModel(Base):
    """Simulation table model."""
    __tablename__ = "simulations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)
    country = Column(String, nullable=False, index=True)
    population_id = Column(String, ForeignKey("populations.id"), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    scenario = relationship("ScenarioDataModel", back_populates="simulations")
    population = relationship("PopulationDataModel", back_populates="simulations")
    budgetary_impacts = relationship("BudgetaryImpactDataModel", back_populates="simulation", cascade="all, delete-orphan")
    decile_impacts = relationship("DecileImpactDataModel", back_populates="simulation", cascade="all, delete-orphan")


# Schema tracking models

class EntityTypeDataModel(Base):
    """Entity type definition table."""
    __tablename__ = "entity_types"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    country = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)  # e.g., "person", "household"
    table_name = Column(String, nullable=False, unique=True)  # e.g., "uk_person"
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    variables = relationship("VariableDataModel", back_populates="entity_type", cascade="all, delete-orphan")


class VariableDataModel(Base):
    """Variable definition table."""
    __tablename__ = "variables"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    entity_type_id = Column(String, ForeignKey("entity_types.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g., "employment_income"
    data_type = Column(String, nullable=False)  # e.g., "float", "integer", "boolean", "string"
    is_nullable = Column(Boolean, default=True)
    default_value = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    entity_type = relationship("EntityTypeDataModel", back_populates="variables")


# Analysis result models

class BudgetaryImpactDataModel(Base):
    """Budgetary impact analysis results."""
    __tablename__ = "budgetary_impacts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    simulation_id = Column(String, ForeignKey("simulations.id"), nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    simulation = relationship("SimulationDataModel", back_populates="budgetary_impacts")


class DecileImpactDataModel(Base):
    """Decile impact analysis results."""
    __tablename__ = "decile_impacts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    simulation_id = Column(String, ForeignKey("simulations.id"), nullable=False)
    decile = Column(Integer, nullable=False)  # 1-10
    decile_variable = Column(String, nullable=False)  # e.g., "income", "wealth"
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    simulation = relationship("SimulationDataModel", back_populates="decile_impacts")