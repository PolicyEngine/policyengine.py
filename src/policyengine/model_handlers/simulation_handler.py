"""Storage-agnostic simulation handler.

This module provides business logic for working with simulations using
Pydantic models, independent of storage implementation.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid
import pandas as pd

from ..data_models import (
    SimulationMetadataModel,
    SimulationDataModel,
    ScenarioModel,
    DatasetModel
)


class SimulationHandler:
    """Handles simulation operations using Pydantic models."""
    
    @staticmethod
    def create_simulation_metadata(
        scenario: Union[ScenarioModel, str],
        dataset: Union[DatasetModel, str],
        country: str,
        year: Optional[int] = None,
        simulation_id: Optional[str] = None,
        model_version: Optional[str] = None,
        status: str = "pending",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> SimulationMetadataModel:
        """Create simulation metadata.
        
        Args:
            scenario: ScenarioModel or scenario name
            dataset: DatasetModel or dataset name
            country: Country code
            year: Simulation year
            simulation_id: Unique ID (generated if not provided)
            model_version: Model version string
            status: Simulation status
            description: Human-readable description
            tags: List of tags for filtering
            
        Returns:
            SimulationMetadataModel instance
        """
        # Handle scenario input
        if isinstance(scenario, str):
            scenario = ScenarioModel(
                name=scenario,
                country=country,
                parameter_changes=[]
            )
        
        # Handle dataset input
        if isinstance(dataset, str):
            dataset = DatasetModel(
                name=dataset,
                country=country,
                year=year
            )
        
        return SimulationMetadataModel(
            id=simulation_id or str(uuid.uuid4()),
            country=country.lower(),
            year=year or datetime.now().year,
            dataset=dataset,
            scenario=scenario,
            model_version=model_version,
            status=status,
            description=description,
            tags=tags or []
        )
    
    @staticmethod
    def process_simulation_data(
        simulation: Any,  # PolicyEngine simulation object
        years: Optional[List[int]] = None,
        calculate_default_variables: bool = True,
        save_all_variables: bool = False,
        country: str = "uk"
    ) -> Dict[int, SimulationDataModel]:
        """Process simulation data from PolicyEngine simulation object.
        
        Args:
            simulation: PolicyEngine simulation object
            years: Years to process
            calculate_default_variables: Calculate default variables
            save_all_variables: Save all calculated variables
            country: Country code for processing
            
        Returns:
            Dictionary mapping year to SimulationDataModel
        """
        if years is None:
            years = [datetime.now().year]
        
        results = {}
        
        for year in years:
            if calculate_default_variables:
                # Process with default variables
                data = SimulationHandler._process_default_variables(
                    simulation, year, country
                )
            elif save_all_variables:
                # Save all variables
                data = SimulationHandler._extract_all_variables(
                    simulation, year
                )
            else:
                # Extract minimal data
                data = SimulationHandler._extract_minimal_data(
                    simulation, year
                )
            
            results[year] = data
        
        return results
    
    @staticmethod
    def _process_default_variables(
        simulation: Any,
        year: int,
        country: str
    ) -> SimulationDataModel:
        """Process simulation with default variables.
        
        Args:
            simulation: PolicyEngine simulation object
            year: Year to process
            country: Country code
            
        Returns:
            SimulationDataModel with processed data
        """
        # Import country-specific processing
        if country.lower() == "uk":
            from ..countries.uk import process_uk_simulation
            model_output = process_uk_simulation(simulation, year)
        elif country.lower() == "us":
            from ..countries.us import process_us_simulation
            model_output = process_us_simulation(simulation, year)
        else:
            # Fallback to basic extraction
            return SimulationHandler._extract_minimal_data(simulation, year)
        
        # Convert to SimulationDataModel
        tables = model_output.get_tables()
        return SimulationDataModel.from_dict(tables)
    
    @staticmethod
    def _extract_all_variables(
        simulation: Any,
        year: int
    ) -> SimulationDataModel:
        """Extract all calculated variables from simulation.
        
        Args:
            simulation: PolicyEngine simulation object
            year: Year to extract
            
        Returns:
            SimulationDataModel with all variables
        """
        data = {}
        
        # Extract all entity data
        entities = ["person", "household", "family", "tax_unit", "marital_unit", "spm_unit", "benefit_unit"]
        
        for entity_name in entities:
            if hasattr(simulation, entity_name):
                entity = getattr(simulation, entity_name)
                entity_data = {}
                
                # Get all variables for this entity
                if hasattr(entity, "_variable_cache"):
                    for var_name in entity._variable_cache:
                        try:
                            values = entity(var_name, year)
                            entity_data[var_name] = values
                        except:
                            continue
                
                if entity_data:
                    data[entity_name] = pd.DataFrame(entity_data)
        
        # Ensure required fields
        if "person" not in data:
            data["person"] = pd.DataFrame()
        if "household" not in data:
            data["household"] = pd.DataFrame()
        
        return SimulationDataModel.from_dict(data)
    
    @staticmethod
    def _extract_minimal_data(
        simulation: Any,
        year: int
    ) -> SimulationDataModel:
        """Extract minimal required data from simulation.
        
        Args:
            simulation: PolicyEngine simulation object
            year: Year to extract
            
        Returns:
            SimulationDataModel with minimal data
        """
        person_data = {}
        household_data = {}
        
        # Extract basic person variables
        try:
            if hasattr(simulation, "person"):
                person = simulation.person
                person_data["person_id"] = person("person_id", year)
                person_data["age"] = person("age", year)
                person_data["household_id"] = person("household_id", year)
        except:
            pass
        
        # Extract basic household variables
        try:
            if hasattr(simulation, "household"):
                household = simulation.household
                household_data["household_id"] = household("household_id", year)
                household_data["household_weight"] = household("household_weight", year)
        except:
            pass
        
        return SimulationDataModel(
            person=pd.DataFrame(person_data) if person_data else pd.DataFrame(),
            household=pd.DataFrame(household_data) if household_data else pd.DataFrame()
        )
    
    @staticmethod
    def validate_simulation_metadata(metadata: SimulationMetadataModel) -> bool:
        """Validate simulation metadata.
        
        Args:
            metadata: SimulationMetadataModel to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        if not metadata.country:
            raise ValueError("Simulation must have a country")
        
        if not metadata.dataset:
            raise ValueError("Simulation must have a dataset")
        
        if not metadata.scenario:
            raise ValueError("Simulation must have a scenario")
        
        valid_statuses = ["pending", "running", "completed", "failed"]
        if metadata.status not in valid_statuses:
            raise ValueError(f"Invalid status: {metadata.status}")
        
        return True
    
    @staticmethod
    def simulation_metadata_to_dict(metadata: SimulationMetadataModel) -> Dict[str, Any]:
        """Convert simulation metadata to dictionary.
        
        Args:
            metadata: SimulationMetadataModel
            
        Returns:
            Dictionary representation
        """
        from .scenario_handler import ScenarioHandler
        from .dataset_handler import DatasetHandler
        
        return {
            "id": metadata.id,
            "country": metadata.country,
            "year": metadata.year,
            "dataset": DatasetHandler.dataset_to_dict(metadata.dataset),
            "scenario": ScenarioHandler.scenario_to_dict(metadata.scenario),
            "model_version": metadata.model_version,
            "status": metadata.status,
            "description": metadata.description,
            "tags": metadata.tags
        }
    
    @staticmethod
    def simulation_metadata_from_dict(data: Dict[str, Any]) -> SimulationMetadataModel:
        """Create simulation metadata from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            SimulationMetadataModel instance
        """
        from .scenario_handler import ScenarioHandler
        from .dataset_handler import DatasetHandler
        
        return SimulationMetadataModel(
            id=data.get("id"),
            country=data["country"],
            year=data.get("year"),
            dataset=DatasetHandler.dataset_from_dict(data["dataset"]),
            scenario=ScenarioHandler.scenario_from_dict(data["scenario"]),
            model_version=data.get("model_version"),
            status=data.get("status", "pending"),
            description=data.get("description"),
            tags=data.get("tags", [])
        )
    
    @staticmethod
    def filter_simulations(
        simulations: List[SimulationMetadataModel],
        country: Optional[str] = None,
        scenario_name: Optional[str] = None,
        dataset_name: Optional[str] = None,
        year: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> List[SimulationMetadataModel]:
        """Filter simulations by criteria.
        
        Args:
            simulations: List of simulations to filter
            country: Filter by country
            scenario_name: Filter by scenario name
            dataset_name: Filter by dataset name
            year: Filter by year
            tags: Filter by tags
            
        Returns:
            Filtered list of SimulationMetadataModel instances
        """
        filtered = simulations
        
        if country:
            filtered = [s for s in filtered if s.country == country.lower()]
        
        if scenario_name:
            filtered = [s for s in filtered if s.scenario.name == scenario_name]
        
        if dataset_name:
            filtered = [s for s in filtered if s.dataset.name == dataset_name]
        
        if year:
            filtered = [s for s in filtered if s.year == year]
        
        if tags:
            tag_set = set(tags)
            filtered = [s for s in filtered if tag_set.intersection(s.tags)]
        
        return filtered