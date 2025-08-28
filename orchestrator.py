"""SimulationOrchestrator - Main interface for PolicyEngine simulations and metadata."""

from typing import Optional, Any, List, Dict, Union, Literal
from pydantic import BaseModel

from .src.policyengine.storage_adapter import StorageAdapter
from .src.policyengine.sql_storage_adapter import SQLStorageAdapter, SQLConfig
from .src.policyengine.database.models import (
    ScenarioMetadata,
    DatasetMetadata,
    SimulationMetadata,
    ReportMetadata,
    VariableMetadata
)


# Storage strategy types
StorageStrategy = Literal["sql"]  # Can be extended to include "mongo", "redis", etc.


class SimulationOrchestrator:
    """Main orchestrator for PolicyEngine simulations.
    
    This class provides a unified interface for managing simulations, scenarios,
    datasets, and reports. It uses the strategy pattern to support different
    storage backends.
    """
    
    def __init__(
        self,
        strategy: StorageStrategy = "sql",
        config: Optional[Union[Dict[str, Any], BaseModel]] = None,
        # Legacy parameters for backward compatibility
        connection_string: Optional[str] = None,
        echo: bool = False,
        storage_mode: str = "local",
        local_storage_path: str = "./simulations",
        gcs_bucket: Optional[str] = None,
        gcs_prefix: str = "simulations/",
        countries: Optional[List[str]] = None,
        initialize: bool = False,
    ):
        """Initialize the SimulationOrchestrator.
        
        Args:
            strategy: Storage strategy to use ('sql' for now)
            config: Strategy-specific configuration object or dict
            connection_string: Database connection string (legacy parameter)
            echo: Echo SQL statements (legacy parameter)
            storage_mode: Storage mode for files (legacy parameter)
            local_storage_path: Local path for files (legacy parameter)
            gcs_bucket: GCS bucket name (legacy parameter)
            gcs_prefix: GCS prefix (legacy parameter)
            countries: List of supported countries
            initialize: Whether to auto-initialize with current law
        """
        self.strategy = strategy
        
        # Handle legacy parameters if config not provided
        if config is None and connection_string is not None:
            # Create config from legacy parameters
            if strategy == "sql":
                config = SQLConfig(
                    connection_string=connection_string,
                    echo=echo,
                    storage_mode=storage_mode,
                    local_storage_path=local_storage_path,
                    gcs_bucket=gcs_bucket,
                    gcs_prefix=gcs_prefix,
                    default_country=countries[0] if countries else "uk"
                )
        elif config is None:
            # Use default config
            if strategy == "sql":
                config = SQLConfig(
                    storage_mode=storage_mode,
                    local_storage_path=local_storage_path,
                    gcs_bucket=gcs_bucket,
                    gcs_prefix=gcs_prefix,
                    default_country=countries[0] if countries else "uk"
                )
        
        # Convert dict to appropriate config object if needed
        if isinstance(config, dict):
            if strategy == "sql":
                config = SQLConfig(**config)
        
        self.config = config
        
        # Initialize the appropriate storage adapter
        if strategy == "sql":
            self.adapter: StorageAdapter = SQLStorageAdapter(config)
        else:
            raise ValueError(f"Unknown storage strategy: {strategy}")
        
        # Set countries for backward compatibility
        self.countries = countries or ["uk"]
        self.default_country = config.default_country if hasattr(config, 'default_country') else self.countries[0]
        
        # Auto-initialize if requested
        if initialize:
            self._auto_initialize()
    
    def _auto_initialize(self) -> None:
        """Automatically initialize with current law parameters for each country."""
        for country in self.countries:
            # Check if current law already exists
            existing = self.get_scenario("current_law", country)
            
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
    
    def _initialize_default_datasets(self, country: str) -> None:
        """Initialize default datasets for a country."""
        # Define default datasets for each country
        default_datasets = {
            "uk": [
                {
                    "name": "frs_2023_24",
                    "year": 2023,
                    "source": "FRS",
                    "description": "Family Resources Survey 2023-24",
                    "filename": "frs_2023_24.h5",
                },
                {
                    "name": "enhanced_frs_2023_24",
                    "year": 2023,
                    "source": "FRS",
                    "description": "Enhanced Family Resources Survey 2023-24",
                    "filename": "enhanced_frs_2023_24.h5",
                }
            ],
            "us": [
                {
                    "name": "cps_2023",
                    "year": 2023,
                    "source": "CPS",
                    "description": "Current Population Survey 2023",
                    "filename": "cps_2023.h5",
                },
                {
                    "name": "enhanced_cps_2024",
                    "year": 2024,
                    "source": "CPS",
                    "description": "Enhanced Current Population Survey 2024",
                    "filename": "enhanced_cps_2024.h5",
                }
            ]
        }
        
        datasets = default_datasets.get(country.lower(), [])
        
        for dataset_info in datasets:
            # Check if dataset already exists
            existing = self.get_dataset(dataset_info["name"], country)
            
            if not existing:
                # Create dataset
                self.create_dataset(
                    name=dataset_info["name"],
                    country=country,
                    year=dataset_info["year"],
                    source=dataset_info["source"],
                    description=dataset_info["description"],
                    filename=dataset_info["filename"]
                )
    
    # ==================== Scenario Management ====================
    
    def create_scenario(
        self,
        name: str,
        parameter_changes: Optional[Dict[str, Any]] = None,
        country: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[ScenarioMetadata]:
        """Create a parametric scenario with parameter changes.
        
        Args:
            name: Unique scenario name
            parameter_changes: Dictionary of parameter changes
            country: Country code
            description: Human-readable description
            
        Returns:
            ScenarioMetadata object or None
        """
        if self.adapter:
            return self.adapter.create_scenario(name, parameter_changes, country, description)
        return None
    
    def get_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[ScenarioMetadata]:
        """Get a scenario by name and country.
        
        Args:
            name: Scenario name
            country: Country code
            
        Returns:
            ScenarioMetadata object or None if not found
        """
        if self.adapter:
            return self.adapter.get_scenario(name, country)
        return None
    
    def get_current_law_scenario(
        self,
        country: Optional[str] = None
    ) -> Optional[ScenarioMetadata]:
        """Get the current law scenario for a country.
        
        Args:
            country: Country code (uses default if not specified)
            
        Returns:
            ScenarioMetadata object or None if not found
        """
        if self.adapter and hasattr(self.adapter, 'get_current_law_scenario'):
            return self.adapter.get_current_law_scenario(country)
        return self.get_scenario("current_law", country)
    
    # ==================== Dataset Management ====================
    
    def create_dataset(
        self,
        name: str,
        country: Optional[str] = None,
        year: Optional[int] = None,
        source: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Optional[DatasetMetadata]:
        """Create a dataset in the database.
        
        Args:
            name: Unique dataset name
            country: Country code
            year: Dataset year
            source: Data source
            version: Dataset version
            description: Description
            filename: Associated file
            
        Returns:
            DatasetMetadata object or None
        """
        if self.adapter:
            return self.adapter.create_dataset(name, country, year, source, version, description, filename)
        return None
    
    def get_dataset(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[DatasetMetadata]:
        """Get a dataset by name and country.
        
        Args:
            name: Dataset name
            country: Country code
            
        Returns:
            DatasetMetadata object or None
        """
        if self.adapter:
            return self.adapter.get_dataset(name, country)
        return None
    
    def list_datasets(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        source: Optional[str] = None
    ) -> List[DatasetMetadata]:
        """List datasets matching criteria.
        
        Args:
            country: Filter by country
            year: Filter by year
            source: Filter by source
            
        Returns:
            List of DatasetMetadata objects
        """
        if self.adapter:
            return self.adapter.list_datasets(country, year, source)
        return []
    
    # ==================== Simulation Management ====================
    
    def create_simulation(
        self,
        scenario: Union[str, ScenarioMetadata],
        simulation: Any,
        dataset: Optional[Union[str, DatasetMetadata]] = None,
        country: Optional[str] = None,
        year: Optional[int] = None,
        years: Optional[List[int]] = None,
        tags: Optional[List[str]] = None,
        calculate_default_variables: bool = True,
        save_all_variables: bool = False,
    ) -> Optional[SimulationMetadata]:
        """Create and store simulation results from a policyengine_core Simulation object.
        
        Args:
            scenario: ScenarioMetadata object or scenario name string
            simulation: Simulation object from policyengine_core
            dataset: DatasetMetadata object or dataset name string
            country: Country code
            year: Single year to save
            years: Multiple years to save
            tags: Optional tags for filtering
            calculate_default_variables: If True, calculates default variables
            save_all_variables: If True, saves all calculated variables
            
        Returns:
            SimulationMetadata object or None
        """
        if self.adapter:
            return self.adapter.create_simulation(
                scenario, simulation, dataset, country, year, years, tags,
                calculate_default_variables, save_all_variables
            )
        return None
    
    def get_simulation(
        self,
        scenario: str,
        dataset: str,
        country: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Optional[SimulationMetadata]:
        """Retrieve simulation metadata.
        
        Args:
            scenario: Scenario name
            dataset: Dataset name
            country: Country code
            year: Simulation year
            
        Returns:
            SimulationMetadata object with get_data() method, or None if not found
        """
        if self.adapter:
            return self.adapter.get_simulation(scenario, dataset, country, year)
        return None
    
    def list_simulations(
        self,
        country: Optional[str] = None,
        scenario: Optional[str] = None,
        dataset: Optional[str] = None,
        year: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> List[SimulationMetadata]:
        """List simulations matching criteria.
        
        Args:
            country: Filter by country
            scenario: Filter by scenario
            dataset: Filter by dataset
            year: Filter by year
            tags: Filter by tags
            
        Returns:
            List of SimulationMetadata objects
        """
        if self.adapter:
            return self.adapter.list_simulations(country, scenario, dataset, year, tags)
        return []
    
    # ==================== Report Management ====================
    
    def create_report(
        self,
        baseline_simulation: Union[str, SimulationMetadata],
        reform_simulation: Union[str, SimulationMetadata],
        year: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        run_immediately: bool = True
    ) -> Optional[Union[ReportMetadata, Dict[str, Any]]]:
        """Create and optionally run an economic impact report.
        
        Args:
            baseline_simulation: Either a SimulationMetadata object or simulation ID string
            reform_simulation: Either a SimulationMetadata object or simulation ID string
            year: Optional year to analyze
            name: Report name
            description: Report description
            run_immediately: Whether to run the analysis immediately
            
        Returns:
            ReportMetadata object or report results dict (if run_immediately), or None
        """
        if self.adapter:
            return self.adapter.create_report(
                baseline_simulation, reform_simulation, year, name, description, run_immediately
            )
        return None
    
    def get_report(
        self,
        report_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a report and its results by ID.
        
        Args:
            report_id: Report ID
            
        Returns:
            Dictionary containing report metadata and results, or None
        """
        if self.adapter:
            return self.adapter.get_report(report_id)
        return None
    
    def list_reports(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ReportMetadata]:
        """List reports matching criteria.
        
        Args:
            country: Filter by country
            year: Filter by year
            status: Filter by status ('pending', 'running', 'completed', 'failed')
            
        Returns:
            List of ReportMetadata objects
        """
        if self.adapter:
            return self.adapter.list_reports(country, year, status)
        return []
    
    # ==================== Variable Management ====================
    
    def get_variable(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[VariableMetadata]:
        """Get a variable by name and country.
        
        Args:
            name: Variable name
            country: Country code
            
        Returns:
            VariableMetadata object or None if not found
        """
        if self.adapter:
            return self.adapter.get_variable(name, country)
        return None
    
    def list_variables(
        self,
        country: Optional[str] = None,
        entity: Optional[str] = None,
        value_type: Optional[str] = None
    ) -> List[VariableMetadata]:
        """List variables matching criteria.
        
        Args:
            country: Filter by country
            entity: Filter by entity (e.g., 'person', 'household')
            value_type: Filter by value type (e.g., 'float', 'bool')
            
        Returns:
            List of VariableMetadata objects
        """
        if self.adapter:
            return self.adapter.list_variables(country, entity, value_type)
        return []
    
    # ==================== Initialization ====================
    
    def initialize_with_current_law(
        self,
        country: str
    ) -> None:
        """Initialize database with current law parameters.
        
        Args:
            country: Country code
        """
        if self.adapter:
            self.adapter.initialize_with_current_law(country)
    
    # ==================== Backward Compatibility Methods ====================
    # These methods exist to maintain backward compatibility with existing code
    
    def session(self):
        """Get a database session context manager (for backward compatibility).
        
        Returns:
            Session context manager if using SQL adapter, None otherwise
        """
        if self.strategy == "sql" and hasattr(self.adapter, 'session'):
            return self.adapter.session()
        
        # Return a dummy context manager for non-SQL strategies
        from contextlib import contextmanager
        
        @contextmanager
        def dummy_session():
            yield None
        
        return dummy_session()
    
    def get_session(self):
        """Get a new database session (for backward compatibility).
        
        Returns:
            SQLAlchemy session if using SQL adapter, None otherwise
        """
        if self.strategy == "sql" and hasattr(self.adapter, 'get_session'):
            return self.adapter.get_session()
        return None
    
    def init_db(self) -> None:
        """Initialize database schema (for backward compatibility)."""
        # SQL adapter initializes schema automatically
        pass
    
    def drop_all(self) -> None:
        """Drop all tables (for backward compatibility - use with caution)."""
        if self.strategy == "sql" and hasattr(self.adapter, 'engine'):
            from .src.policyengine.database.models import Base
            Base.metadata.drop_all(bind=self.adapter.engine)
    
    def get_report_results(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_report (for backward compatibility)."""
        return self.get_report(report_id)
    
    # ==================== Context Manager Support ====================
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if hasattr(self.adapter, 'close'):
            self.adapter.close()