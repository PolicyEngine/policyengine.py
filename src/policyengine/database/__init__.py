"""Database abstraction for PolicyEngine with hybrid storage."""

from .database import Database, DatabaseConfig
from .models import (
    SimulationMetadata,
    DatasetMetadata,
    ScenarioMetadata,
    ParameterMetadata,
    ParameterChangeMetadata,
    SimulationStatus
)
from .parameter_utils import (
    import_parameters_from_tax_benefit_system,
    extract_parameter_metadata,
    extract_parameter_changes,
    get_parameter_value_at_instant,
    apply_parameter_changes_to_simulation
)
from .storage_backend import StorageBackend
from .scenario_manager import ScenarioManager
from .dataset_manager import DatasetManager
from .simulation_manager import SimulationManager

__all__ = [
    # Main classes
    "Database",
    "DatabaseConfig",
    
    # Models
    "SimulationMetadata",
    "DatasetMetadata",
    "ScenarioMetadata",
    "ParameterMetadata",
    "ParameterChangeMetadata",
    "SimulationStatus",
    
    # Managers (for advanced use)
    "StorageBackend",
    "ScenarioManager",
    "DatasetManager",
    "SimulationManager",
    
    # Utilities
    "import_parameters_from_tax_benefit_system",
    "extract_parameter_metadata",
    "extract_parameter_changes",
    "get_parameter_value_at_instant",
    "apply_parameter_changes_to_simulation",
]