"""Default pass-through storage adapter for PolicyEngine.

This module implements a simple pass-through storage adapter that doesn't persist
data. It simply returns the schema objects passed to it. Useful for testing,
temporary computations, and when persistence isn't needed.
"""

from typing import Optional, Any, List, Dict, Union

from .storage_adapter import StorageAdapter
from .data_models import (
    ScenarioModel,
    DatasetModel,
    SimulationMetadataModel,
    ReportMetadataModel,
)


class DefaultStorageAdapter(StorageAdapter):
    """Default pass-through storage adapter implementation.
    
    This adapter doesn't store any data. It simply returns the
    schema objects passed to it, acting as a pass-through layer.
    Useful for testing and temporary computations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the default storage adapter.
        
        Args:
            config: Optional configuration dictionary (unused for default adapter)
        """
        super().__init__(config)
    
    # ==================== Scenario Management ====================
    
    def create_scenario(
        self,
        scenario: ScenarioModel,
    ) -> ScenarioModel:
        """Pass through a scenario model."""
        return scenario
    
    def get_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[ScenarioModel]:
        """Return None - no storage in pass-through adapter."""
        return None
    
    def list_scenarios(
        self,
        country: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ScenarioModel]:
        """Return empty list - no storage in pass-through adapter."""
        return []
    
    def delete_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> bool:
        """Return False - no storage in pass-through adapter."""
        return False
    
    # ==================== Dataset Management ====================
    
    def create_dataset(
        self,
        dataset: DatasetModel,
    ) -> DatasetModel:
        """Pass through a dataset model."""
        return dataset
    
    def get_dataset(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[DatasetModel]:
        """Return None - no storage in pass-through adapter."""
        return None
    
    def list_datasets(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        source: Optional[str] = None
    ) -> List[DatasetModel]:
        """Return empty list - no storage in pass-through adapter."""
        return []
    
    # ==================== Simulation Management ====================
    
    def create_simulation(
        self,
        simulation_metadata: SimulationMetadataModel,
        simulation: Any,
        calculate_default_variables: bool = True,
        save_all_variables: bool = False,
    ) -> SimulationMetadataModel:
        """Pass through a simulation metadata model."""
        # Store the actual simulation object in the metadata if needed
        return simulation_metadata
    
    def get_simulation(
        self,
        scenario: str,
        dataset: str,
        country: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Optional[SimulationMetadataModel]:
        """Return None - no storage in pass-through adapter."""
        return None
    
    def list_simulations(
        self,
        country: Optional[str] = None,
        scenario: Optional[str] = None,
        dataset: Optional[str] = None,
        year: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> List[SimulationMetadataModel]:
        """Return empty list - no storage in pass-through adapter."""
        return []
    
    def delete_simulation(
        self,
        simulation_id: str
    ) -> bool:
        """Return False - no storage in pass-through adapter."""
        return False
    
    # ==================== Report Management ====================
    
    def create_report(
        self,
        report_metadata: ReportMetadataModel,
        baseline_simulation: Union[str, Any],
        reform_simulation: Union[str, Any],
        run_immediately: bool = True
    ) -> ReportMetadataModel:
        """Pass through a report metadata model."""
        return report_metadata
    
    def get_report(
        self,
        report_id: str
    ) -> Optional[ReportMetadataModel]:
        """Return None - no storage in pass-through adapter."""
        return None
    
    def list_reports(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ReportMetadataModel]:
        """Return empty list - no storage in pass-through adapter."""
        return []
    
    # ==================== Variable Management ====================
    
    def get_variable(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[Any]:
        """Return None - no storage in pass-through adapter."""
        return None
    
    def list_variables(
        self,
        country: Optional[str] = None,
        entity: Optional[str] = None,
        value_type: Optional[str] = None
    ) -> List[Any]:
        """Return empty list - no storage in pass-through adapter."""
        return []
    
    # ==================== Initialization ====================
    
    def initialize_with_current_law(
        self,
        country: str
    ) -> None:
        """Initialize with current law - no-op for pass-through adapter."""
        # Pass-through adapter doesn't store anything
        pass
    
    # ==================== Storage Operations ====================
    
    def save_simulation_data(
        self,
        simulation_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Return a dummy URI - no storage in pass-through adapter."""
        return f"passthrough://{simulation_id}"
    
    def load_simulation_data(
        self,
        simulation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return None - no storage in pass-through adapter."""
        return None