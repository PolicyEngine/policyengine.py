"""Database management for PolicyEngine simulations and metadata."""

import os
from typing import Optional, Dict, Any, List, Union
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, and_, or_, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pydantic import BaseModel, Field
from .models import (
    Base, SimulationMetadata, SimulationStatus,
    DatasetMetadata, ScenarioMetadata, ParameterMetadata, ParameterChangeMetadata
)
from .parameter_utils import import_parameters_from_tax_benefit_system
import h5py
import json
import numpy as np


class DatabaseConfig(BaseModel):
    """Configuration for database connection and storage."""
    
    # Database configuration
    connection_string: Optional[str] = Field(
        None, 
        description="Database connection string for metadata (defaults to local SQLite)"
    )
    echo: bool = Field(False, description="Echo SQL statements")
    
    # Storage configuration
    storage_mode: str = Field("local", description="Storage mode: 'local' or 'cloud'")
    local_storage_path: str = Field("./simulations", description="Local path for .h5 files")
    
    # Cloud configuration (optional)
    gcs_bucket: Optional[str] = Field(None, description="Google Cloud Storage bucket name")
    gcs_prefix: Optional[str] = Field("simulations/", description="Prefix for GCS objects")
    cloud_db_url: Optional[str] = Field(None, description="Cloud database URL for metadata")


class Database:
    """Main database manager for PolicyEngine."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize database with configuration.
        
        Args:
            config: Database configuration
        """
        self.config = config or DatabaseConfig()
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
        
        # Ensure storage directories exist
        if self.config.storage_mode == "local":
            self._setup_local_storage()
    
    def _create_engine(self):
        """Create SQLAlchemy engine for metadata storage."""
        if self.config.storage_mode == "cloud" and self.config.cloud_db_url:
            # Use cloud database for metadata
            return create_engine(
                self.config.cloud_db_url,
                echo=self.config.echo,
                pool_size=5,
                max_overflow=10
            )
        elif self.config.connection_string:
            # Custom connection string provided
            return create_engine(
                self.config.connection_string,
                echo=self.config.echo
            )
        else:
            # Default to local SQLite
            db_path = os.path.join(self.config.local_storage_path, "metadata.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            engine = create_engine(
                f"sqlite:///{db_path}",
            )
            
            return engine
    
    def _setup_local_storage(self):
        """Ensure local storage directories exist."""
        storage_path = Path(self.config.local_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (storage_path / "uk").mkdir(exist_ok=True)
        (storage_path / "us").mkdir(exist_ok=True)
        (storage_path / "temp").mkdir(exist_ok=True)
    
    @contextmanager
    def session(self) -> Session:
        """Get a database session context manager.
        
        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session(self) -> Session:
        """Get a new database session.
        
        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()
    
    def init_db(self) -> None:
        """Initialize database schema."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_all(self) -> None:
        """Drop all tables (use with caution)."""
        Base.metadata.drop_all(bind=self.engine)
    
    def initialize_with_current_law(
        self,
        country: str = "uk",
        max_parameters: Optional[int] = None
    ) -> Dict[str, Any]:
        """Initialize database with current law parameters.
        
        Args:
            country: Country code ('uk' or 'us')
            max_parameters: Maximum number of parameters to import (None = all)
            
        Returns:
            Created current law scenario
        """
        
        # Import the appropriate country system
        if country.lower() == "uk":
            from policyengine_uk import CountryTaxBenefitSystem
            system = CountryTaxBenefitSystem()
        elif country.lower() == "us":
            from policyengine_us import CountryTaxBenefitSystem
            system = CountryTaxBenefitSystem()
        else:
            raise ValueError(f"Unsupported country: {country}")
        
        # Import parameters into database
        with self.session() as session:
            import_parameters_from_tax_benefit_system(
                session=session,
                tax_benefit_system=system,
                country=country.lower(),
                scenario_name=f"current_law",
                scenario_description=f"Current model baseline",
                max_parameters=max_parameters
            )
    
    def get_current_law_scenario(
        self,
        country: str,
        year: Optional[int] = None
    ) -> Optional[ScenarioMetadata]:
        """Get the current law scenario for a country and year.
        
        Args:
            country: Country code
            year: Year (defaults to current year)
            
        Returns:
            Current law scenario or None if not found
        """
        if year is None:
            year = datetime.now().year
            
        with self.session() as session:
            scenario = session.query(ScenarioMetadata).filter_by(
                name=f"current law",
                country=country.lower()
            ).first()
            
            return scenario