"""SimulationOrchestrator abstraction for PolicyEngine with hybrid storage."""

from .models import (
    SimulationMetadata,
    DatasetMetadata,
    ScenarioMetadata,
    ParameterMetadata,
    ParameterChangeMetadata,
    SimulationStatus,
    VariableMetadata,
    User,
    ReportMetadata,
    UKGovernmentBudget,
    UKHouseholdIncome,
    UKDecileImpact,
    UKPovertyImpact,
    UKInequalityImpact,
    UKWinnersLosers,
    USGovernmentBudget,
    USHouseholdIncome,
    USDecileImpact,
    USPovertyImpact,
    USInequalityImpact,
    USWinnersLosers,
    USProgramImpact,
)
from ..utils import (
    import_parameters_from_tax_benefit_system,
    extract_parameter_metadata,
    extract_parameter_changes,
    get_parameter_value_at_instant,
    apply_parameter_changes_to_simulation,
    import_variables_from_tax_benefit_system,
    extract_variable_metadata
)
from .storage_backend import StorageBackend
from .scenario_manager import ScenarioManager
from .dataset_manager import DatasetManager
from .simulation_manager import SimulationManager
from .report_manager import ReportManager

__all__ = [
    # Main classes
    "SimulationOrchestrator",
    
    # Models
    "SimulationMetadata",
    "DatasetMetadata",
    "ScenarioMetadata",
    "ParameterMetadata",
    "ParameterChangeMetadata",
    "VariableMetadata",
    "User",
    "SimulationStatus",
    "ReportMetadata",
    "UKGovernmentBudget",
    "UKHouseholdIncome",
    "UKDecileImpact",
    "UKPovertyImpact",
    "UKInequalityImpact",
    "UKWinnersLosers",
    "USGovernmentBudget",
    "USHouseholdIncome",
    "USDecileImpact",
    "USPovertyImpact",
    "USInequalityImpact",
    "USWinnersLosers",
    "USProgramImpact",
    
    # Managers (for advanced use)
    "StorageBackend",
    "ScenarioManager",
    "DatasetManager",
    "SimulationManager",
    "ReportManager",
    
    # Utilities
    "import_parameters_from_tax_benefit_system",
    "extract_parameter_metadata",
    "extract_parameter_changes",
    "get_parameter_value_at_instant",
    "apply_parameter_changes_to_simulation",
    "import_variables_from_tax_benefit_system",
    "extract_variable_metadata",
]