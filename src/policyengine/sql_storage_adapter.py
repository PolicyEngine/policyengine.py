"""SQL storage adapter for PolicyEngine.

This module implements the StorageAdapter interface for SQL databases,
supporting SQLite, PostgreSQL, MySQL, and other SQLAlchemy-compatible databases.
"""

import os
import uuid
from typing import Optional, Any, List, Dict, Union
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pydantic import BaseModel, Field

from .storage_adapter import StorageAdapter
from .data_models import (
    ScenarioModel,
    DatasetModel,
    SimulationMetadataModel,
    ReportMetadataModel,
)
from .database.models import (
    Base,
    ScenarioMetadata,
    DatasetMetadata,
    SimulationMetadata,
    SimulationStatus,
    ParameterMetadata,
    ParameterChangeMetadata,
    VariableMetadata,
    ReportMetadata,
    get_model_version
)
from .database.storage_backend import StorageBackend
from .database.scenario_manager import ScenarioManager
from .database.dataset_manager import DatasetManager
from .database.simulation_manager import SimulationManager
from .database.report_manager import ReportManager
from .utils import (
    import_parameters_from_tax_benefit_system,
    import_variables_from_tax_benefit_system
)


class SQLConfig(BaseModel):
    """Configuration for SQL database connection and storage."""
    
    # Database configuration
    connection_string: Optional[str] = Field(
        None,
        description="Database connection string (SQLite, PostgreSQL, MySQL, etc. - defaults to local SQLite)"
    )
    echo: bool = Field(False, description="Echo SQL statements")
    
    # Connection pool settings
    pool_size: int = Field(5, description="Number of connections to maintain in pool")
    max_overflow: int = Field(10, description="Maximum overflow connections above pool_size")
    pool_timeout: float = Field(30.0, description="Timeout for getting connection from pool")
    pool_recycle: int = Field(3600, description="Recycle connections after this many seconds")
    
    # Storage configuration for .h5 simulation files
    storage_mode: str = Field("local", description="Storage mode for .h5 files: 'local' or 'cloud'")
    local_storage_path: str = Field("./simulations", description="Local path for .h5 files")
    
    # Cloud storage configuration for .h5 files (optional)
    gcs_bucket: Optional[str] = Field(None, description="Google Cloud Storage bucket name for .h5 files")
    gcs_prefix: Optional[str] = Field("simulations/", description="Prefix for GCS objects")
    
    # Default country
    default_country: Optional[str] = Field(None, description="Default country code")


class SQLStorageAdapter(StorageAdapter):
    """SQL storage adapter implementation.
    
    This adapter uses SQLAlchemy to support multiple SQL databases including
    SQLite, PostgreSQL, MySQL, and others. Metadata is stored in the database
    while simulation data files (.h5) are stored separately (locally or in cloud).
    """
    
    def __init__(self, config: SQLConfig):
        """Initialize SQL storage adapter.
        
        Args:
            config: SQL configuration object
        """
        super().__init__(config.dict())
        self.config = config
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize managers
        self.storage_backend = StorageBackend(self.config)
        self.scenario_manager = ScenarioManager(self.config.default_country)
        self.dataset_manager = DatasetManager(self.config.default_country)
        self.simulation_manager = SimulationManager(self.storage_backend, self.config.default_country)
        self.report_manager = None  # Initialized on demand
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
        
        # Ensure storage directories exist
        if self.config.storage_mode == "local":
            self._setup_local_storage()
    
    def _create_engine(self):
        """Create SQLAlchemy engine for metadata storage."""
        if self.config.connection_string:
            # Use provided connection string
            return create_engine(
                self.config.connection_string,
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle
            )
        else:
            # Default to local SQLite
            db_path = os.path.join(self.config.local_storage_path, "metadata.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            return create_engine(
                f"sqlite:///{db_path}",
                echo=self.config.echo,
                connect_args={'check_same_thread': False},
                poolclass=StaticPool
            )
    
    def _setup_local_storage(self):
        """Ensure local storage directories exist."""
        storage_path = Path(self.config.local_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
    
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
    
    # ==================== Scenario Management ====================
    
    def create_scenario(
        self,
        scenario: ScenarioModel,
    ) -> ScenarioMetadata:
        """Create a scenario with parameter changes."""
        # Convert parameter changes to dict format for SQL adapter
        parameter_changes = {pc.parameter_name: pc.value for pc in scenario.parameter_changes}
        
        with self.session() as session:
            return self.scenario_manager.create_scenario(
                session, scenario.name, parameter_changes, scenario.country, scenario.description
            )
    
    def get_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[ScenarioMetadata]:
        """Retrieve a scenario by name and country."""
        with self.session() as session:
            scenario = self.scenario_manager.get_scenario(session, name, country)
            if scenario:
                session.expunge_all()
            return scenario
    
    def list_scenarios(
        self,
        country: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ScenarioMetadata]:
        """List scenarios matching criteria."""
        country = country or self.config.default_country
        
        with self.session() as session:
            query = session.query(ScenarioMetadata)
            
            if country:
                query = query.filter_by(country=country.lower())
            
            if limit:
                query = query.limit(limit)
            
            scenarios = query.all()
            
            for scenario in scenarios:
                session.expunge(scenario)
            
            return scenarios
    
    def delete_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> bool:
        """Delete a scenario."""
        country = country or self.config.default_country
        
        with self.session() as session:
            scenario = session.query(ScenarioMetadata).filter_by(
                name=name,
                country=country.lower()
            ).first()
            
            if scenario:
                session.delete(scenario)
                session.commit()
                return True
            
            return False
    
    # ==================== Dataset Management ====================
    
    def create_dataset(
        self,
        dataset: DatasetModel,
    ) -> DatasetMetadata:
        """Create a dataset."""
        with self.session() as session:
            return self.dataset_manager.create_dataset(
                session, dataset.name, dataset.country, dataset.year, 
                dataset.source, dataset.version, dataset.description, None  # filename not in model
            )
    
    def get_dataset(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[DatasetMetadata]:
        """Retrieve a dataset by name and country."""
        with self.session() as session:
            dataset = self.dataset_manager.get_dataset(session, name, country)
            if dataset:
                session.expunge(dataset)
            return dataset
    
    def list_datasets(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        source: Optional[str] = None
    ) -> List[DatasetMetadata]:
        """List datasets matching criteria."""
        with self.session() as session:
            datasets = self.dataset_manager.list_datasets(session, country, year, source)
            for dataset in datasets:
                session.expunge(dataset)
            return datasets
    
    # ==================== Simulation Management ====================
    
    def create_simulation(
        self,
        simulation_metadata: SimulationMetadataModel,
        simulation: Any,
        calculate_default_variables: bool = True,
        save_all_variables: bool = False,
    ) -> SimulationMetadata:
        """Create and store simulation results."""
        # Extract values from metadata model
        scenario_name = simulation_metadata.scenario.name
        dataset_name = simulation_metadata.dataset.name
        country = simulation_metadata.country
        year = simulation_metadata.year
        years = [year] if year else []
        tags = simulation_metadata.tags
        
        with self.session() as session:
            result = self.simulation_manager.create_simulation(
                session, scenario_name, simulation, dataset_name,
                country, year, years, tags,
                calculate_default_variables, save_all_variables
            )
            # Attach storage backend for data access
            result._storage = self.storage_backend
            return result
    
    def get_simulation(
        self,
        scenario: str,
        dataset: str,
        country: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Optional[SimulationMetadata]:
        """Retrieve simulation results."""
        with self.session() as session:
            result = self.simulation_manager.get_simulation_metadata(
                session, scenario, dataset, country, year
            )
            if result:
                # Attach storage backend for data access
                result._storage = self.storage_backend
            return result
    
    def list_simulations(
        self,
        country: Optional[str] = None,
        scenario: Optional[str] = None,
        dataset: Optional[str] = None,
        year: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> List[SimulationMetadata]:
        """List simulations matching criteria."""
        with self.session() as session:
            simulations = self.simulation_manager.list_simulations(
                session, country, scenario, dataset, year, tags
            )
            # Attach storage backend to each simulation
            for sim in simulations:
                sim._storage = self.storage_backend
            return simulations
    
    def delete_simulation(
        self,
        simulation_id: str
    ) -> bool:
        """Delete a simulation."""
        with self.session() as session:
            simulation = session.query(SimulationMetadata).filter_by(id=simulation_id).first()
            
            if simulation:
                # Delete the file
                if self.config.storage_mode == "local":
                    filepath = os.path.join(self.config.local_storage_path, f"{simulation_id}.h5")
                    if os.path.exists(filepath):
                        os.remove(filepath)
                
                # Delete metadata
                session.delete(simulation)
                session.commit()
                return True
            
            return False
    
    # ==================== Report Management ====================
    
    def create_report(
        self,
        report_metadata: ReportMetadataModel,
        baseline_simulation: Union[str, SimulationMetadata],
        reform_simulation: Union[str, SimulationMetadata],
        run_immediately: bool = True
    ) -> Union[ReportMetadata, Dict[str, Any]]:
        """Create an economic impact report."""
        with self.session() as session:
            if not self.report_manager:
                self.report_manager = ReportManager(session)
            
            # Get simulation IDs
            if isinstance(baseline_simulation, str):
                baseline_id = baseline_simulation
                baseline_sim = session.query(SimulationMetadata).filter_by(id=baseline_id).first()
                if not baseline_sim:
                    raise ValueError(f"Baseline simulation {baseline_id} not found")
            else:
                baseline_id = baseline_simulation.id
                baseline_sim = baseline_simulation
            
            if isinstance(reform_simulation, str):
                reform_id = reform_simulation
                reform_sim = session.query(SimulationMetadata).filter_by(id=reform_id).first()
                if not reform_sim:
                    raise ValueError(f"Reform simulation {reform_id} not found")
            else:
                reform_id = reform_simulation.id
                reform_sim = reform_simulation
            
            # Validate simulations are from same country
            if baseline_sim.country != reform_sim.country:
                raise ValueError(f"Simulations must be from same country")
            
            # Create report metadata
            report = self.report_manager.create_report(
                name=report_metadata.name,
                baseline_simulation_id=baseline_id,
                comparison_simulation_id=reform_id,
                country=baseline_sim.country,
                year=report_metadata.year or baseline_sim.year,
                description=report_metadata.description,
            )
            
            if run_immediately:
                # Load and run analysis
                baseline_sim._storage = self.storage_backend
                reform_sim._storage = self.storage_backend
                
                baseline_data = baseline_sim.get_data(year)
                reform_data = reform_sim.get_data(year)
                
                if baseline_data is None:
                    raise ValueError(f"No data found for baseline simulation")
                if reform_data is None:
                    raise ValueError(f"No data found for reform simulation")
                
                # Run the report
                self.report_manager.run_report(report.id, baseline_data, reform_data)
                
                # Return results
                return self.report_manager.get_report_results(report.id)
            else:
                return report
    
    def get_report(
        self,
        report_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a report by ID."""
        with self.session() as session:
            if not self.report_manager:
                self.report_manager = ReportManager(session)
            
            return self.report_manager.get_report_results(report_id)
    
    def list_reports(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ReportMetadata]:
        """List reports matching criteria."""
        with self.session() as session:
            if not self.report_manager:
                self.report_manager = ReportManager(session)
            
            # Convert status string to enum if provided
            status_enum = None
            if status:
                status_enum = SimulationStatus(status)
            
            reports = self.report_manager.list_reports(
                country=country,
                year=year,
                status=status_enum
            )
            
            for report in reports:
                session.expunge(report)
            
            return reports
    
    # ==================== Variable Management ====================
    
    def get_variable(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[VariableMetadata]:
        """Get a variable by name and country."""
        country = country or self.config.default_country
        
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
        country: Optional[str] = None,
        entity: Optional[str] = None,
        value_type: Optional[str] = None
    ) -> List[VariableMetadata]:
        """List variables matching criteria."""
        country = country or self.config.default_country
        
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
    
    # ==================== Initialization ====================
    
    def initialize_with_current_law(
        self,
        country: str
    ) -> None:
        """Initialize storage with current law parameters."""
        if not country:
            raise ValueError("Country must be specified")
        
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
        country: Optional[str] = None
    ) -> Optional[ScenarioMetadata]:
        """Get the current law scenario for a country."""
        country = country or self.config.default_country
        
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
    
    # ==================== Storage Operations ====================
    
    def save_simulation_data(
        self,
        simulation_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save raw simulation data."""
        # Use storage backend to save
        country = metadata.get('country', 'unknown') if metadata else 'unknown'
        scenario = metadata.get('scenario', 'unknown') if metadata else 'unknown'
        dataset = metadata.get('dataset', 'unknown') if metadata else 'unknown'
        year = metadata.get('year', datetime.now().year) if metadata else datetime.now().year
        
        filepath, file_size = self.storage_backend.save_simulation(
            sim_id=simulation_id,
            country=country,
            scenario=scenario,
            dataset=dataset,
            year=year,
            data=data
        )
        
        return filepath
    
    def load_simulation_data(
        self,
        simulation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load raw simulation data."""
        # Use storage backend to load
        return self.storage_backend.load_simulation(
            sim_id=simulation_id,
            country=None,  # Not needed for loading by ID
            scenario=None,
            dataset=None,
            year=None
        )
    
    # ==================== Utility Methods ====================
    
    def close(self) -> None:
        """Close database connections."""
        if hasattr(self, 'engine'):
            self.engine.dispose()