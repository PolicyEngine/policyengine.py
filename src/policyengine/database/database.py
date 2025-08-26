"""Database management for PolicyEngine simulations and metadata."""

import os
from typing import Optional, Any, List
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pydantic import BaseModel, Field

from .models import Base
from .parameter_utils import import_parameters_from_tax_benefit_system
from .storage_backend import StorageBackend
from .scenario_manager import ScenarioManager
from .dataset_manager import DatasetManager
from .simulation_manager import SimulationManager


class DatabaseConfig(BaseModel):
    """Configuration for database connection and storage."""
    
    # Database configuration
    connection_string: Optional[str] = Field(
        None, 
        description="Database connection string (SQLite, PostgreSQL, MySQL, etc. - defaults to local SQLite)"
    )
    echo: bool = Field(False, description="Echo SQL statements")
    
    # Storage configuration for .h5 simulation files
    storage_mode: str = Field("local", description="Storage mode for .h5 files: 'local' or 'cloud'")
    local_storage_path: str = Field("./simulations", description="Local path for .h5 files")
    
    # Cloud storage configuration for .h5 files (optional)
    gcs_bucket: Optional[str] = Field(None, description="Google Cloud Storage bucket name for .h5 files")
    gcs_prefix: Optional[str] = Field("simulations/", description="Prefix for GCS objects")


class Database:
    """Main database manager for PolicyEngine."""
    
    def __init__(
            self,
            # Database configuration
            connection_string: Optional[str] = None,
            echo: bool = False,
            # Storage configuration
            storage_mode: str = "local",
            local_storage_path: str = "./simulations",
            gcs_bucket: Optional[str] = None,
            gcs_prefix: str = "simulations/",
            # Other options
            countries: Optional[List[str]] = None,
            initialize: bool = False,
        ):
        """Initialize database with configuration.
        
        Args:
            connection_string: Database connection string (SQLite, PostgreSQL, MySQL, etc)
            echo: Echo SQL statements
            storage_mode: Storage mode for .h5 files ('local' or 'cloud')
            local_storage_path: Local path for .h5 files
            gcs_bucket: Google Cloud Storage bucket name for .h5 files
            gcs_prefix: Prefix for GCS objects
            countries: List of supported countries (defaults to ["uk"])
            initialize: Whether to automatically initialize with current law parameters
        """
        self.config = DatabaseConfig(
            connection_string=connection_string,
            echo=echo,
            storage_mode=storage_mode,
            local_storage_path=local_storage_path,
            gcs_bucket=gcs_bucket,
            gcs_prefix=gcs_prefix
        )
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Set default countries and default_country
        if countries is None:
            self.countries = ["uk"]
            self.default_country = "uk"
        else:
            self.countries = countries
            # If only one country, use it as default. Otherwise default to UK if in list, else first
            if len(countries) == 1:
                self.default_country = countries[0]
            elif "uk" in countries:
                self.default_country = "uk"
            else:
                self.default_country = countries[0]
        
        # Initialize managers
        self.storage = StorageBackend(self.config)
        self.scenarios = ScenarioManager(self.default_country)
        self.datasets = DatasetManager(self.default_country)
        self.simulations = SimulationManager(self.storage, self.default_country)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
        
        # Ensure storage directories exist
        if self.config.storage_mode == "local":
            self._setup_local_storage()
        
        # Automatically initialize with current law parameters if requested
        if initialize:
            self._auto_initialize()
    
    def _create_engine(self):
        """Create SQLAlchemy engine for metadata storage.
        
        The database stores metadata only - actual simulation data is in .h5 files.
        Supports any SQLAlchemy-compatible database (SQLite, PostgreSQL, MySQL, etc).
        """
        if self.config.connection_string:
            # Use provided connection string (can be local or cloud database)
            # Examples:
            # - sqlite:///path/to/db.sqlite
            # - postgresql://user:pass@host/dbname
            # - mysql+pymysql://user:pass@host/dbname
            return create_engine(
                self.config.connection_string,
                echo=self.config.echo
            )
        else:
            # Default to local SQLite in the storage path
            db_path = os.path.join(self.config.local_storage_path, "metadata.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            return create_engine(
                f"sqlite:///{db_path}",
                echo=self.config.echo
            )
    
    def _setup_local_storage(self):
        """Ensure local storage directories exist."""
        storage_path = Path(self.config.local_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
    
    def _auto_initialize(self):
        """Automatically initialize database with current law parameters for each country."""
        from .models import ScenarioMetadata
        
        for country in self.countries:
            # Check if current_law scenario already exists
            with self.session() as session:
                existing = session.query(ScenarioMetadata).filter_by(
                    name="current_law",
                    country=country.lower()
                ).first()
                
                if not existing:
                    try:
                        print(f"Initializing {country.upper()} current law parameters and variables...")
                        self.initialize_with_current_law(country)
                    except ImportError:
                        print(f"Note: policyengine-{country} not installed, skipping initialization")
                    except Exception as e:
                        print(f"Warning: Could not initialize {country} parameters: {e}")
            
            # Initialize default datasets
            self._initialize_default_datasets(country)
    
    def _initialize_default_datasets(self, country: str):
        """Initialize default datasets for a country with DataFile references.
        
        Args:
            country: Country code ('uk' or 'us')
        """
        from .models import DatasetMetadata
        
        # Define default datasets for each country
        default_datasets = {
            "uk": [
                {
                    "name": "frs_2023_24",
                    "year": 2023,
                    "source": "FRS",
                    "description": "Family Resources Survey 2023-24",
                    "filename": "frs_2023_24.h5",
                    "gcs_bucket": "policyengine-uk-data-private",
                    "gcs_path": "frs_2023_24.h5"
                },
                {
                    "name": "enhanced_frs_2023_24",
                    "year": 2023,
                    "source": "FRS",
                    "description": "Enhanced Family Resources Survey 2023-24 with imputed wealth",
                    "filename": "enhanced_frs_2023_24.h5",
                    "gcs_bucket": "policyengine-uk-data-private",
                    "gcs_path": "enhanced_frs_2023_24.h5"
                }
            ],
            "us": [
                {
                    "name": "cps_2023",
                    "year": 2023,
                    "source": "CPS",
                    "description": "Current Population Survey 2023",
                    "filename": "cps_2023.h5",
                    "gcs_bucket": "policyengine-us-data",
                    "gcs_path": "cps_2023.h5"
                },
                {
                    "name": "enhanced_cps_2024",
                    "year": 2024,
                    "source": "CPS",
                    "description": "Enhanced Current Population Survey 2024",
                    "filename": "enhanced_cps_2024.h5",
                    "gcs_bucket": "policyengine-us-data",
                    "gcs_path": "enhanced_cps_2024.h5"
                }
            ]
        }
        
        datasets = default_datasets.get(country.lower(), [])
        
        if not datasets:
            return
        
        with self.session() as session:
            for dataset_info in datasets:
                # Check if dataset already exists
                existing = session.query(DatasetMetadata).filter_by(
                    name=dataset_info["name"],
                    country=country.lower()
                ).first()
                
                if not existing:
                    # Create dataset with file information
                    self.datasets.add_dataset(
                        session=session,
                        name=dataset_info["name"],
                        country=country,
                        year=dataset_info["year"],
                        source=dataset_info["source"],
                        description=dataset_info["description"],
                        filename=dataset_info["filename"],
                        gcs_bucket=dataset_info["gcs_bucket"],
                        gcs_path=dataset_info["gcs_path"]
                    )
    
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
    
    # Parameter initialization
    def initialize_with_current_law(
        self,
        country: str = None
    ) -> None:
        """Initialize database with current law parameters.
        
        Args:
            country: Country code (uses default if not specified)
        """
        country = country or self.default_country
        if not country:
            raise ValueError("Country must be specified or set as default")
        
        # Import the appropriate country system
        if country.lower() == "uk":
            from policyengine_uk import CountryTaxBenefitSystem
            system = CountryTaxBenefitSystem()
        elif country.lower() == "us":
            from policyengine_us import CountryTaxBenefitSystem
            system = CountryTaxBenefitSystem()
        else:
            raise ValueError(f"Unsupported country: {country}")
        
        # Import parameters and variables into database
        with self.session() as session:
            from .variable_utils import import_variables_from_tax_benefit_system
            
            # Import parameters
            import_parameters_from_tax_benefit_system(
                session=session,
                tax_benefit_system=system,
                country=country.lower(),
                scenario_name="current_law",
                scenario_description="Current model baseline"
            )
            
            # Import variables
            variable_count = import_variables_from_tax_benefit_system(
                session=session,
                tax_benefit_system=system,
                country=country.lower()
            )
            
            if variable_count > 0:
                print(f"Imported {variable_count} new variables for {country.upper()}")
    
    def get_current_law_scenario(
        self,
        country: str = None
    ):
        """Get the current law scenario for a country.
        
        Args:
            country: Country code (uses default if not specified)
            
        Returns:
            ScenarioMetadata object or None if not found
        """
        from .models import ScenarioMetadata
        country = country or self.default_country
        
        with self.session() as session:
            from sqlalchemy.orm import joinedload
            scenario = session.query(ScenarioMetadata).options(
                joinedload(ScenarioMetadata.parameter_changes)
            ).filter_by(
                name="current_law",
                country=country.lower()
            ).first()
            
            if scenario:
                session.expunge_all()
            
            return scenario
    
    # Scenario management (delegated to ScenarioManager)
    def add_scenario(
        self,
        name: str,
        parameter_changes: dict = None,
        country: str = None,
        description: str = None,
    ):
        """Add a parametric scenario with parameter changes.
        
        See ScenarioManager for documentation on parameter change formats.
        Returns ScenarioMetadata object.
        """
        with self.session() as session:
            return self.scenarios.add_scenario(
                session, name, parameter_changes, country, description
            )
    
    def get_scenario(
        self,
        name: str,
        country: str = None
    ):
        """Get a scenario by name and country.
        
        Returns:
            ScenarioMetadata object or None if not found
        """
        with self.session() as session:
            return self.scenarios.get_scenario(
                session, name, country
            )
    
    # Dataset management (delegated to DatasetManager)
    def add_dataset(
        self,
        name: str,
        country: str = None,
        year: int = None,
        source: str = None,
        version: str = None,
        description: str = None,
    ):
        """Register a dataset in the database. Returns DatasetMetadata object."""
        with self.session() as session:
            return self.datasets.add_dataset(
                session, name, country, year, source, version, description
            )
    
    def get_dataset(
        self,
        name: str,
        country: str = None
    ):
        """Get a dataset by name and country. Returns DatasetMetadata object or None."""
        with self.session() as session:
            return self.datasets.get_dataset(session, name, country)
    
    def list_datasets(
        self,
        country: str = None,
        year: int = None,
        source: str = None
    ):
        """List datasets matching criteria. Returns list of DatasetMetadata objects."""
        with self.session() as session:
            return self.datasets.list_datasets(session, country, year, source)
    
    # Simulation management (delegated to SimulationManager)
    def add_simulation(
        self,
        scenario: Any,  # Can be ScenarioMetadata object or string
        simulation: Any,
        dataset: Any = None,  # Can be DatasetMetadata object or string
        country: str = None,
        year: int = None,
        years: List[int] = None,
        tags: List[str] = None,
        calculate_default_variables: bool = True,
        save_all_variables: bool = False,
    ):
        """Store simulation results from a policyengine_core Simulation object.
        
        Args:
            scenario: ScenarioMetadata object or scenario name string
            simulation: Simulation object from policyengine_core
            dataset: DatasetMetadata object or dataset name string (optional)
            country: Country code (optional, extracted from scenario/dataset if objects provided)
            year: Single year to save (if specified, only saves this year)
            years: Multiple years to save (if specified, saves all these years)
            tags: Optional tags for filtering
            calculate_default_variables: If True, calculates household net income etc.
            save_all_variables: If True, saves all calculated variables for all periods
        
        Returns:
            SimulationMetadata object with get_data() method
        """
        # Extract names and country from objects if provided
        if hasattr(scenario, 'name'):
            # It's a ScenarioMetadata object
            scenario_name = scenario.name
            country = country or scenario.country
        else:
            # It's a string
            scenario_name = scenario
        
        if dataset and hasattr(dataset, 'name'):
            # It's a DatasetMetadata object
            dataset_name = dataset.name
            country = country or dataset.country
        else:
            # It's a string or None
            dataset_name = dataset
        
        with self.session() as session:
            return self.simulations.add_simulation(
                session, scenario_name, simulation, dataset_name, 
                country, year, years, tags, 
                calculate_default_variables, save_all_variables
            )
    
    def get_simulation(
        self,
        scenario: str,
        dataset: str,
        country: str = None,
        year: int = None,
    ):
        """Retrieve simulation metadata.
        
        Returns:
            SimulationMetadata object with get_data() method, or None if not found
        """
        with self.session() as session:
            return self.simulations.get_simulation_metadata(
                session, scenario, dataset, country, year
            )
    
    def list_simulations(
        self,
        country: str = None,
        scenario: str = None,
        dataset: str = None,
        year: int = None,
        tags: List[str] = None
    ):
        """List simulations matching criteria. Returns list of SimulationMetadata objects."""
        with self.session() as session:
            return self.simulations.list_simulations(
                session, country, scenario, dataset, year, tags
            )
    
    # Variable management
    def get_variable(
        self,
        name: str,
        country: str = None
    ):
        """Get a variable by name and country.
        
        Returns:
            VariableMetadata object or None if not found
        """
        from .models import VariableMetadata
        country = country or self.default_country
        
        with self.session() as session:
            variable = session.query(VariableMetadata).filter_by(
                name=name,
                country=country.lower()
            ).first()
            
            if variable:
                session.expunge(variable)
            
            return variable
    
    def list_variables(
        self,
        country: str = None,
        entity: str = None,
        value_type: str = None
    ):
        """List variables matching criteria.
        
        Args:
            country: Filter by country
            entity: Filter by entity (e.g., 'person', 'household')
            value_type: Filter by value type (e.g., 'float', 'bool')
            
        Returns:
            List of VariableMetadata objects
        """
        from .models import VariableMetadata
        country = country or self.default_country
        
        with self.session() as session:
            query = session.query(VariableMetadata)
            
            if country:
                query = query.filter_by(country=country.lower())
            
            if entity:
                query = query.filter_by(entity=entity)
            
            if value_type:
                query = query.filter_by(value_type=value_type)
            
            variables = query.order_by(VariableMetadata.name).all()
            
            for var in variables:
                session.expunge(var)
            
            return variables