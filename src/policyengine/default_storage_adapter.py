"""Default in-memory storage adapter for PolicyEngine.

This module implements a simple in-memory storage adapter that doesn't persist
data. Useful for testing, temporary computations, and when persistence isn't needed.
"""

from typing import Optional, Any, List, Dict, Union
from datetime import datetime
import uuid

from .storage_adapter import StorageAdapter
from .data_models import (
    ScenarioModel,
    DatasetModel,
    SimulationMetadataModel,
    ReportMetadataModel,
)


class DefaultStorageAdapter(StorageAdapter):
    """Default in-memory storage adapter implementation.
    
    This adapter stores all data in memory without persistence.
    Data is lost when the adapter is destroyed or the program exits.
    Useful for testing and temporary computations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the default storage adapter.
        
        Args:
            config: Optional configuration dictionary (unused for default adapter)
        """
        super().__init__(config)
        
        # In-memory storage
        self.scenarios: Dict[str, Dict] = {}
        self.datasets: Dict[str, Dict] = {}
        self.simulations: Dict[str, Dict] = {}
        self.reports: Dict[str, Dict] = {}
        self.variables: Dict[str, Dict] = {}
        self.simulation_data: Dict[str, Any] = {}
    
    # ==================== Scenario Management ====================
    
    def create_scenario(
        self,
        scenario: ScenarioModel,
    ) -> Dict[str, Any]:
        """Create a scenario with parameter changes."""
        scenario_key = f"{scenario.country}_{scenario.name}"
        scenario_dict = {
            "id": str(uuid.uuid4()),
            "name": scenario.name,
            "parameter_changes": {pc.parameter_name: pc.value for pc in scenario.parameter_changes},
            "country": scenario.country,
            "description": scenario.description,
            "created_at": datetime.now().isoformat()
        }
        self.scenarios[scenario_key] = scenario_dict
        return scenario_dict
    
    def get_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a scenario by name and country."""
        scenario_key = f"{country or 'default'}_{name}"
        return self.scenarios.get(scenario_key)
    
    def list_scenarios(
        self,
        country: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List scenarios matching criteria."""
        scenarios = []
        for scenario in self.scenarios.values():
            if country and scenario.get("country") != country:
                continue
            scenarios.append(scenario)
            if limit and len(scenarios) >= limit:
                break
        return scenarios
    
    def delete_scenario(
        self,
        name: str,
        country: Optional[str] = None
    ) -> bool:
        """Delete a scenario."""
        scenario_key = f"{country or 'default'}_{name}"
        if scenario_key in self.scenarios:
            del self.scenarios[scenario_key]
            return True
        return False
    
    # ==================== Dataset Management ====================
    
    def create_dataset(
        self,
        dataset: DatasetModel,
    ) -> Dict[str, Any]:
        """Create a dataset."""
        dataset_key = f"{dataset.country}_{dataset.name}"
        dataset_dict = {
            "id": str(uuid.uuid4()),
            "name": dataset.name,
            "country": dataset.country,
            "year": dataset.year,
            "source": dataset.source,
            "version": dataset.version,
            "description": dataset.description,
            "filename": None,  # Not in DatasetModel
            "created_at": datetime.now().isoformat()
        }
        self.datasets[dataset_key] = dataset_dict
        return dataset_dict
    
    def get_dataset(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a dataset by name and country."""
        dataset_key = f"{country or 'default'}_{name}"
        return self.datasets.get(dataset_key)
    
    def list_datasets(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List datasets matching criteria."""
        datasets = []
        for dataset in self.datasets.values():
            if country and dataset.get("country") != country:
                continue
            if year and dataset.get("year") != year:
                continue
            if source and dataset.get("source") != source:
                continue
            datasets.append(dataset)
        return datasets
    
    # ==================== Simulation Management ====================
    
    def create_simulation(
        self,
        simulation_metadata: SimulationMetadataModel,
        simulation: Any,
        calculate_default_variables: bool = True,
        save_all_variables: bool = False,
    ) -> Dict[str, Any]:
        """Create and store simulation results."""
        sim_id = simulation_metadata.id or str(uuid.uuid4())
        simulation_obj = {
            "id": sim_id,
            "scenario": simulation_metadata.scenario.name,
            "dataset": simulation_metadata.dataset.name,
            "country": simulation_metadata.country,
            "year": simulation_metadata.year,
            "years": [simulation_metadata.year] if simulation_metadata.year else [],
            "tags": simulation_metadata.tags,
            "created_at": datetime.now().isoformat(),
            "calculate_default_variables": calculate_default_variables,
            "save_all_variables": save_all_variables,
            "data": simulation  # Store the actual simulation object
        }
        
        # Create key for retrieval
        sim_key = f"{simulation_metadata.country}_{simulation_metadata.scenario.name}_{simulation_metadata.dataset.name}_{simulation_metadata.year}"
        self.simulations[sim_key] = simulation_obj
        self.simulations[sim_id] = simulation_obj  # Also store by ID
        
        return simulation_obj
    
    def get_simulation(
        self,
        scenario: str,
        dataset: str,
        country: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve simulation results."""
        sim_key = f"{country or 'default'}_{scenario}_{dataset}_{year}"
        return self.simulations.get(sim_key)
    
    def list_simulations(
        self,
        country: Optional[str] = None,
        scenario: Optional[str] = None,
        dataset: Optional[str] = None,
        year: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List simulations matching criteria."""
        simulations = []
        seen_ids = set()
        for sim in self.simulations.values():
            # Skip duplicates (we store by both key and ID)
            if sim["id"] in seen_ids:
                continue
            seen_ids.add(sim["id"])
            
            if country and sim.get("country") != country:
                continue
            if scenario and sim.get("scenario") != scenario:
                continue
            if dataset and sim.get("dataset") != dataset:
                continue
            if year and year not in sim.get("years", []):
                continue
            if tags and not set(tags).intersection(sim.get("tags", [])):
                continue
            simulations.append(sim)
        return simulations
    
    def delete_simulation(
        self,
        simulation_id: str
    ) -> bool:
        """Delete a simulation."""
        if simulation_id in self.simulations:
            del self.simulations[simulation_id]
            return True
        return False
    
    # ==================== Report Management ====================
    
    def create_report(
        self,
        report_metadata: ReportMetadataModel,
        baseline_simulation: Union[str, Any],
        reform_simulation: Union[str, Any],
        run_immediately: bool = True
    ) -> Dict[str, Any]:
        """Create an economic impact report."""
        report_id = report_metadata.id or str(uuid.uuid4())
        
        # Extract IDs
        baseline_id = baseline_simulation if isinstance(baseline_simulation, str) else baseline_simulation.get("id")
        reform_id = reform_simulation if isinstance(reform_simulation, str) else reform_simulation.get("id")
        
        report = {
            "id": report_id,
            "name": report_metadata.name,
            "baseline_simulation_id": baseline_id,
            "reform_simulation_id": reform_id,
            "year": report_metadata.year,
            "description": report_metadata.description,
            "created_at": datetime.now().isoformat(),
            "status": "completed" if run_immediately else "pending",
            "results": {}
        }
        
        if run_immediately:
            # Simple mock results for in-memory adapter
            report["results"] = {
                "budget_impact": {"value": 0, "unit": "currency"},
                "household_impact": {"value": 0, "unit": "currency"},
                "poverty_impact": {"value": 0, "unit": "percentage"},
                "inequality_impact": {"value": 0, "unit": "gini"},
                "message": "In-memory adapter: actual computation not implemented"
            }
        
        self.reports[report_id] = report
        return report
    
    def get_report(
        self,
        report_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a report by ID."""
        return self.reports.get(report_id)
    
    def list_reports(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List reports matching criteria."""
        reports = []
        for report in self.reports.values():
            if year and report.get("year") != year:
                continue
            if status and report.get("status") != status:
                continue
            reports.append(report)
        return reports
    
    # ==================== Variable Management ====================
    
    def get_variable(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a variable by name and country."""
        var_key = f"{country or 'default'}_{name}"
        return self.variables.get(var_key)
    
    def list_variables(
        self,
        country: Optional[str] = None,
        entity: Optional[str] = None,
        value_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List variables matching criteria."""
        variables = []
        for var in self.variables.values():
            if country and var.get("country") != country:
                continue
            if entity and var.get("entity") != entity:
                continue
            if value_type and var.get("value_type") != value_type:
                continue
            variables.append(var)
        return variables
    
    # ==================== Initialization ====================
    
    def initialize_with_current_law(
        self,
        country: str
    ) -> None:
        """Initialize storage with current law parameters."""
        # For in-memory adapter, just create a current law scenario
        self.create_scenario(
            name="current_law",
            parameter_changes={},
            country=country,
            description=f"Current law baseline for {country}"
        )
    
    # ==================== Storage Operations ====================
    
    def save_simulation_data(
        self,
        simulation_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save raw simulation data."""
        self.simulation_data[simulation_id] = {
            "data": data,
            "metadata": metadata or {},
            "saved_at": datetime.now().isoformat()
        }
        return f"memory://{simulation_id}"
    
    def load_simulation_data(
        self,
        simulation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load raw simulation data."""
        stored = self.simulation_data.get(simulation_id)
        if stored:
            return stored.get("data")
        return None