"""SimulationOrchestrator - Main interface for PolicyEngine simulations and metadata."""

from typing import Optional, Any, List, Dict, Union, Literal
from pydantic import BaseModel
from datetime import datetime
import uuid

from .src.policyengine.storage_adapter import StorageAdapter
from .src.policyengine.default_storage_adapter import DefaultStorageAdapter
from .src.policyengine.sql_storage_adapter import SQLStorageAdapter, SQLConfig
from .src.policyengine.data_models import (
    ScenarioModel,
    ParameterChangeModel,
    DatasetModel,
    SimulationMetadataModel,
    ReportMetadataModel,
)


# Storage method types
StorageMethod = Literal["default", "sql"]  # Can be extended to include "mongo", "redis", etc.


class SimulationOrchestrator:
    """Main orchestrator for PolicyEngine simulations.
    
    This class provides a unified interface for managing simulations, scenarios,
    datasets, and reports. It uses the strategy pattern to support different
    storage backends.
    """
    
    def __init__(
        self,
        storage_method: StorageMethod = "default",
        config: Optional[Union[Dict[str, Any], BaseModel]] = None,
        countries: Optional[List[str]] = None,
        initialize: bool = False,
    ):
        """Initialize the SimulationOrchestrator.
        
        Args:
            storage_method: Storage method to use ('default' for in-memory, 'sql' for database)
            config: Storage-specific configuration object or dict
            countries: List of supported countries
            initialize: Whether to auto-initialize with current law
        """
        self.storage_method = storage_method
        self.config = config
        
        # Initialize the appropriate storage adapter
        if storage_method == "default":
            self.adapter: StorageAdapter = DefaultStorageAdapter(config.dict() if hasattr(config, 'dict') else config)
        elif storage_method == "sql":
            if not isinstance(config, SQLConfig):
                if config is None:
                    config = SQLConfig()
                elif isinstance(config, dict):
                    config = SQLConfig(**config)
            self.adapter: StorageAdapter = SQLStorageAdapter(config)
        else:
            raise ValueError(f"Unknown storage method: {storage_method}")
        
        # Set countries
        self.countries = countries or ["uk"]
        self.default_country = self.countries[0]
        
        # Update adapter's default country if it has one
        if hasattr(self.adapter, 'config') and hasattr(self.adapter.config, 'default_country'):
            self.adapter.config.default_country = self.default_country
        
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
                    description=dataset_info["description"]
                )
    
    # ==================== Scenario Management ====================
    
    def create_scenario(
        self,
        name: str,
        parameter_changes: Optional[Dict[str, Any]] = None,
        country: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Any:
        """Create a parametric scenario with parameter changes.
        
        Args:
            name: Unique scenario name
            parameter_changes: Dictionary of parameter changes
            country: Country code
            description: Human-readable description
            
        Returns:
            Created scenario object
        """
        # Convert parameter_changes dict to ParameterChangeModel instances
        param_change_models = []
        if parameter_changes:
            for param_name, value_or_dict in parameter_changes.items():
                if isinstance(value_or_dict, dict):
                    # Format: {"2025-01-01": value}
                    for date_str, value in value_or_dict.items():
                        param_change_models.append(
                            ParameterChangeModel(
                                parameter_name=param_name,
                                start_date=datetime.fromisoformat(date_str),
                                value=value,
                            )
                        )
                else:
                    # Simple value format
                    param_change_models.append(
                        ParameterChangeModel(
                            parameter_name=param_name,
                            start_date=datetime.now(),
                            value=value_or_dict,
                        )
                    )
        
        # Create ScenarioModel
        scenario_model = ScenarioModel(
            name=name,
            country=country or self.default_country,
            description=description,
            parameter_changes=param_change_models,
        )
        
        # Pass the model to the adapter
        return self.adapter.create_scenario(scenario_model)
    
    def get_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[Any]:
        """Get a scenario by name and country.
        
        Args:
            name: Scenario name
            country: Country code
            
        Returns:
            Scenario object or None if not found
        """
        return self.adapter.get_scenario(name, country)
    
    def get_current_law_scenario(
        self,
        country: Optional[str] = None
    ) -> Optional[Any]:
        """Get the current law scenario for a country.
        
        Args:
            country: Country code (uses default if not specified)
            
        Returns:
            Scenario object or None if not found
        """
        if hasattr(self.adapter, 'get_current_law_scenario'):
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
    ) -> Any:
        """Create a dataset.
        
        Args:
            name: Unique dataset name
            country: Country code
            year: Dataset year
            source: Data source
            version: Dataset version
            description: Description
            
        Returns:
            Created dataset object
        """
        # Create DatasetModel
        dataset_model = DatasetModel(
            name=name,
            country=country or self.default_country,
            year=year,
            source=source,
            version=version,
            description=description,
        )
        
        # Pass the model to the adapter
        return self.adapter.create_dataset(dataset_model)
    
    def get_dataset(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[Any]:
        """Get a dataset by name and country.
        
        Args:
            name: Dataset name
            country: Country code
            
        Returns:
            Dataset object or None
        """
        return self.adapter.get_dataset(name, country)
    
    def list_datasets(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        source: Optional[str] = None
    ) -> List[Any]:
        """List datasets matching criteria.
        
        Args:
            country: Filter by country
            year: Filter by year
            source: Filter by source
            
        Returns:
            List of dataset objects
        """
        return self.adapter.list_datasets(country, year, source)
    
    # ==================== Simulation Management ====================
    
    def create_simulation(
        self,
        scenario: Union[str, Any],
        simulation: Any,
        dataset: Optional[Union[str, Any]] = None,
        country: Optional[str] = None,
        year: Optional[int] = None,
        years: Optional[List[int]] = None,
        tags: Optional[List[str]] = None,
        calculate_default_variables: bool = True,
        save_all_variables: bool = False,
    ) -> Any:
        """Create and store simulation results from a policyengine_core Simulation object.
        
        Args:
            scenario: Scenario object or scenario name string
            simulation: Simulation object from policyengine_core
            dataset: Dataset object or dataset name string
            country: Country code
            year: Single year to save
            years: Multiple years to save
            tags: Optional tags for filtering
            calculate_default_variables: If True, calculates default variables
            save_all_variables: If True, saves all calculated variables
            
        Returns:
            Created simulation object
        """
        # Convert to model instances if needed
        scenario_model = scenario if isinstance(scenario, ScenarioModel) else ScenarioModel(
            name=scenario if isinstance(scenario, str) else scenario.get("name"),
            country=country or self.default_country,
            description="",
            parameter_changes=[],
        )
        
        dataset_model = dataset if isinstance(dataset, DatasetModel) else DatasetModel(
            name=dataset if isinstance(dataset, str) else (dataset.get("name") if dataset else "unknown"),
            country=country or self.default_country,
            year=year,
        )
        
        # Create SimulationMetadataModel
        simulation_metadata = SimulationMetadataModel(
            id=str(uuid.uuid4()),
            country=country or self.default_country,
            year=year,
            dataset=dataset_model,
            scenario=scenario_model,
            tags=tags or [],
        )
        
        # Pass the model to the adapter
        return self.adapter.create_simulation(
            simulation_metadata, simulation,
            calculate_default_variables, save_all_variables
        )
    
    def get_simulation(
        self,
        scenario: str,
        dataset: str,
        country: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Optional[Any]:
        """Retrieve simulation metadata.
        
        Args:
            scenario: Scenario name
            dataset: Dataset name
            country: Country code
            year: Simulation year
            
        Returns:
            Simulation object or None if not found
        """
        return self.adapter.get_simulation(scenario, dataset, country, year)
    
    def list_simulations(
        self,
        country: Optional[str] = None,
        scenario: Optional[str] = None,
        dataset: Optional[str] = None,
        year: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> List[Any]:
        """List simulations matching criteria.
        
        Args:
            country: Filter by country
            scenario: Filter by scenario
            dataset: Filter by dataset
            year: Filter by year
            tags: Filter by tags
            
        Returns:
            List of simulation objects
        """
        return self.adapter.list_simulations(country, scenario, dataset, year, tags)
    
    # ==================== Report Management ====================
    
    def create_report(
        self,
        baseline_simulation: Union[str, Any],
        reform_simulation: Union[str, Any],
        year: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        run_immediately: bool = True
    ) -> Any:
        """Create and optionally run an economic impact report.
        
        Args:
            baseline_simulation: Baseline simulation object or ID
            reform_simulation: Reform simulation object or ID
            year: Optional year to analyze
            name: Report name
            description: Report description
            run_immediately: Whether to run the analysis immediately
            
        Returns:
            Report object or results
        """
        # Extract IDs
        baseline_id = baseline_simulation if isinstance(baseline_simulation, str) else baseline_simulation.get("id")
        comparison_id = reform_simulation if isinstance(reform_simulation, str) else reform_simulation.get("id")
        
        # Create ReportMetadataModel
        report_metadata = ReportMetadataModel(
            id=str(uuid.uuid4()),
            name=name or f"Report {datetime.now().isoformat()}",
            country=self.default_country,
            year=year,
            baseline_simulation_id=baseline_id,
            comparison_simulation_id=comparison_id,
            description=description,
        )
        
        # Pass the model to the adapter
        return self.adapter.create_report(
            report_metadata, baseline_simulation, reform_simulation, run_immediately
        )
    
    def get_report(
        self,
        report_id: str
    ) -> Optional[Any]:
        """Get a report and its results by ID.
        
        Args:
            report_id: Report ID
            
        Returns:
            Report object or None
        """
        return self.adapter.get_report(report_id)
    
    def list_reports(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Any]:
        """List reports matching criteria.
        
        Args:
            country: Filter by country
            year: Filter by year
            status: Filter by status
            
        Returns:
            List of report objects
        """
        return self.adapter.list_reports(country, year, status)
    
    # ==================== Variable Management ====================
    
    def get_variable(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[Any]:
        """Get a variable by name and country.
        
        Args:
            name: Variable name
            country: Country code
            
        Returns:
            Variable object or None if not found
        """
        return self.adapter.get_variable(name, country)
    
    def list_variables(
        self,
        country: Optional[str] = None,
        entity: Optional[str] = None,
        value_type: Optional[str] = None
    ) -> List[Any]:
        """List variables matching criteria.
        
        Args:
            country: Filter by country
            entity: Filter by entity (e.g., 'person', 'household')
            value_type: Filter by value type (e.g., 'float', 'bool')
            
        Returns:
            List of variable objects
        """
        return self.adapter.list_variables(country, entity, value_type)
    
    # ==================== Initialization ====================
    
    def initialize_with_current_law(
        self,
        country: str
    ) -> None:
        """Initialize storage with current law parameters.
        
        Args:
            country: Country code
        """
        self.adapter.initialize_with_current_law(country)
    
    # ==================== SQL-specific compatibility methods ====================
    
    def session(self):
        """Get a database session context manager (SQL adapter only).
        
        Returns:
            Session context manager if using SQL adapter, dummy context otherwise
        """
        if self.storage_method == "sql" and hasattr(self.adapter, 'session'):
            return self.adapter.session()
        
        # Return a dummy context manager for non-SQL storage methods
        from contextlib import contextmanager
        
        @contextmanager
        def dummy_session():
            yield None
        
        return dummy_session()
    
    def get_session(self):
        """Get a new database session (SQL adapter only).
        
        Returns:
            SQLAlchemy session if using SQL adapter, None otherwise
        """
        if self.storage_method == "sql" and hasattr(self.adapter, 'get_session'):
            return self.adapter.get_session()
        return None
    
    # ==================== Context Manager Support ====================
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if hasattr(self.adapter, 'close'):
            self.adapter.close()