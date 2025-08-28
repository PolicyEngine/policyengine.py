"""Base storage adapter interface for PolicyEngine.

This module defines the abstract base class for all storage adapters.
Storage adapters implement the strategy pattern, allowing different
storage backends (SQL, NoSQL, file-based, etc.) to be used interchangeably.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict, Union
from datetime import datetime


class StorageAdapter(ABC):
    """Abstract base class for storage adapters.
    
    This class defines the interface that all storage adapters must implement.
    Subclasses should provide concrete implementations for their specific
    storage backend (e.g., SQLStorageAdapter, MongoStorageAdapter, etc.).
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the storage adapter.
        
        Args:
            config: Optional configuration dictionary for the storage backend
        """
        self.config = config or {}
    
    # ==================== Scenario Management ====================
    
    @abstractmethod
    def create_scenario(
        self,
        name: str,
        parameter_changes: Optional[Dict[str, Any]] = None,
        country: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Any:
        """Create a scenario with parameter changes.
        
        Args:
            name: Unique name for the scenario
            parameter_changes: Dictionary of parameter changes
            country: Country code (e.g., 'uk', 'us')
            description: Human-readable description
            
        Returns:
            Created scenario object or identifier
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement create_scenario")
    
    @abstractmethod
    def get_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[Any]:
        """Retrieve a scenario by name and country.
        
        Args:
            name: Scenario name
            country: Country code
            
        Returns:
            Scenario object or None if not found
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement get_scenario")
    
    @abstractmethod
    def list_scenarios(
        self,
        country: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Any]:
        """List scenarios matching criteria.
        
        Args:
            country: Filter by country code
            limit: Maximum number of results
            
        Returns:
            List of scenario objects
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement list_scenarios")
    
    @abstractmethod
    def delete_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> bool:
        """Delete a scenario.
        
        Args:
            name: Scenario name
            country: Country code
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement delete_scenario")
    
    # ==================== Dataset Management ====================
    
    @abstractmethod
    def create_dataset(
        self,
        name: str,
        country: Optional[str] = None,
        year: Optional[int] = None,
        source: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Any:
        """Create a dataset.
        
        Args:
            name: Unique dataset name
            country: Country code
            year: Dataset year
            source: Data source (e.g., 'FRS', 'CPS')
            version: Dataset version
            description: Human-readable description
            filename: Associated file name
            
        Returns:
            Created dataset object or identifier
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement create_dataset")
    
    @abstractmethod
    def get_dataset(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[Any]:
        """Retrieve a dataset by name and country.
        
        Args:
            name: Dataset name
            country: Country code
            
        Returns:
            Dataset object or None if not found
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement get_dataset")
    
    @abstractmethod
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
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement list_datasets")
    
    # ==================== Simulation Management ====================
    
    @abstractmethod
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
        """Create and store simulation results.
        
        Args:
            scenario: Scenario name or object
            simulation: Simulation object from policyengine_core
            dataset: Dataset name or object
            country: Country code
            year: Single year to save
            years: Multiple years to save
            tags: Optional tags for filtering
            calculate_default_variables: If True, calculates default variables
            save_all_variables: If True, saves all variables
            
        Returns:
            Created simulation object or identifier
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement create_simulation")
    
    @abstractmethod
    def get_simulation(
        self,
        scenario: str,
        dataset: str,
        country: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Optional[Any]:
        """Retrieve simulation results.
        
        Args:
            scenario: Scenario name
            dataset: Dataset name
            country: Country code
            year: Simulation year
            
        Returns:
            Simulation object or None if not found
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement get_simulation")
    
    @abstractmethod
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
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement list_simulations")
    
    @abstractmethod
    def delete_simulation(
        self,
        simulation_id: str
    ) -> bool:
        """Delete a simulation.
        
        Args:
            simulation_id: Simulation identifier
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement delete_simulation")
    
    # ==================== Report Management ====================
    
    @abstractmethod
    def create_report(
        self,
        baseline_simulation: Union[str, Any],
        reform_simulation: Union[str, Any],
        year: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        run_immediately: bool = True
    ) -> Any:
        """Create an economic impact report.
        
        Args:
            baseline_simulation: Baseline simulation ID or object
            reform_simulation: Reform simulation ID or object
            year: Year to analyze
            name: Report name
            description: Report description
            run_immediately: Whether to run analysis immediately
            
        Returns:
            Report object or results
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement create_report")
    
    @abstractmethod
    def get_report(
        self,
        report_id: str
    ) -> Optional[Any]:
        """Retrieve a report by ID.
        
        Args:
            report_id: Report identifier
            
        Returns:
            Report object or None if not found
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement get_report")
    
    @abstractmethod
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
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement list_reports")
    
    # ==================== Variable Management ====================
    
    @abstractmethod
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
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement get_variable")
    
    @abstractmethod
    def list_variables(
        self,
        country: Optional[str] = None,
        entity: Optional[str] = None,
        value_type: Optional[str] = None
    ) -> List[Any]:
        """List variables matching criteria.
        
        Args:
            country: Filter by country
            entity: Filter by entity type (e.g., 'person', 'household')
            value_type: Filter by value type (e.g., 'float', 'bool')
            
        Returns:
            List of variable objects
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement list_variables")
    
    # ==================== Initialization ====================
    
    @abstractmethod
    def initialize_with_current_law(
        self,
        country: str
    ) -> None:
        """Initialize storage with current law parameters.
        
        Args:
            country: Country code
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement initialize_with_current_law")
    
    # ==================== Storage Operations ====================
    
    @abstractmethod
    def save_simulation_data(
        self,
        simulation_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save raw simulation data.
        
        Args:
            simulation_id: Unique identifier for the simulation
            data: Simulation data to save
            metadata: Optional metadata about the simulation
            
        Returns:
            Storage location or identifier
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement save_simulation_data")
    
    @abstractmethod
    def load_simulation_data(
        self,
        simulation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load raw simulation data.
        
        Args:
            simulation_id: Simulation identifier
            
        Returns:
            Simulation data or None if not found
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement load_simulation_data")
    
    # ==================== Utility Methods ====================
    
    def close(self) -> None:
        """Close any open connections or resources.
        
        Subclasses should override this if they need to clean up resources.
        """
        pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()