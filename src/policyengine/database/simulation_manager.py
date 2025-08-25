"""Simulation management functions."""

import uuid
from datetime import datetime
from typing import Any, Optional, List, Union, Dict
from sqlalchemy.orm import Session
from .models import SimulationMetadata, SimulationStatus, ScenarioMetadata, DatasetMetadata, DataFile, get_model_version
from .storage_backend import StorageBackend
from ..countries.uk import UKModelOutput
from ..countries.us import USModelOutput


class SimulationManager:
    """Manages simulation storage and retrieval."""
    
    def __init__(self, storage_backend: StorageBackend, default_country: Optional[str] = None):
        """Initialize simulation manager.
        
        Args:
            storage_backend: Storage backend for file operations
            default_country: Default country to use when not specified
        """
        self.storage = storage_backend
        self.default_country = default_country
    
    def add_simulation(
        self,
        session: Session,
        scenario: str,
        simulation: Any,  # Simulation from policyengine_core
        dataset: str = None,
        country: str = None,
        year: int = None,
        years: List[int] = None,
        tags: List[str] = None,
        calculate_default_variables: bool = True,
        save_all_variables: bool = False,
    ) -> SimulationMetadata:
        """Store simulation results.
        
        Args:
            session: Database session
            scenario: Name of the scenario used
            simulation: Simulation object from policyengine_core
            dataset: Name of the dataset used (optional, extracted from simulation if not provided)
            country: Country code (uses default if not specified)
            year: Single year to save (if specified, only saves this year)
            years: Multiple years to save (if specified, saves all these years)
            tags: Optional tags for filtering
            calculate_default_variables: If True, calculates household net income etc.
            save_all_variables: If True, saves all calculated variables for all periods
            
        Returns:
            Created SimulationMetadata object
        """
        country = country or self.default_country
        if not country:
            raise ValueError("Country must be specified or set as default")
        
        # Determine which years to process
        if year is not None:
            years_to_process = [year]
        elif years is not None:
            years_to_process = years
        else:
            # Default to current year
            years_to_process = [datetime.now().year]
        
        # Collect data for all years
        all_data = {}
        
        if calculate_default_variables:
            # Import the correct country-specific process_simulation
            if country == 'us':
                from ..countries.us import process_us_simulation as process_simulation
            else:
                from ..countries.uk import process_uk_simulation as process_simulation
            
            # Process for each year
            for process_year in years_to_process:
                model_output = process_simulation(simulation, process_year).get_tables()
                all_data[process_year] = model_output
        elif save_all_variables:
            # Save all calculated variables organized by year and entity
            all_data = self._extract_all_variables(simulation, years_to_process)
        else:
            # Save specific variables for the requested years
            for process_year in years_to_process:
                all_data[process_year] = self._extract_year_data(simulation, process_year)
        
        # Verify scenario exists
        scenario_obj = session.query(ScenarioMetadata).filter_by(
            name=scenario,
            country=country.lower()
        ).first()
        
        if not scenario_obj:
            raise ValueError(f"Scenario '{scenario}' not found for country '{country}'")
        
        # Verify dataset if specified
        dataset_obj = None
        if dataset:
            dataset_obj = session.query(DatasetMetadata).filter_by(
                name=dataset,
                country=country.lower()
            ).first()
            
            if not dataset_obj:
                # Create dataset entry if it doesn't exist
                dataset_obj = DatasetMetadata(
                    id=str(uuid.uuid4()),
                    name=dataset,
                    country=country.lower(),
                    year=years_to_process[0] if years_to_process else datetime.now().year,
                    model_version=get_model_version(country)
                )
                session.add(dataset_obj)
                session.flush()
        
        # Generate unique ID for simulation
        sim_id = str(uuid.uuid4())
        
        # Save simulation data (now with multi-year structure)
        filepath, file_size_mb = self.storage.save_simulation(
            sim_id=sim_id,
            country=country,
            scenario=scenario,
            dataset=dataset,
            year=years_to_process[0] if len(years_to_process) == 1 else None,  # For backward compat
            data=all_data  # Now contains {year: data} structure
        )
        
        # Create DataFile entry for the simulation
        datafile = None
        if filepath:
            # Create datafile entry
            datafile = DataFile(
                id=str(uuid.uuid4()),
                filename=f"{sim_id}.h5",
                local_path=filepath if self.storage.config.storage_mode == "local" else None,
                gcs_bucket=self.storage.config.gcs_bucket if self.storage.config.storage_mode == "cloud" else None,
                gcs_path=filepath if self.storage.config.storage_mode == "cloud" else None,
                file_size_mb=file_size_mb
            )
            session.add(datafile)
            session.flush()
        
        # Link dataset's datafile to simulation if available
        if dataset_obj and hasattr(dataset_obj, 'datafile') and dataset_obj.datafile:
            # Simulation uses the same datafile as its source dataset
            simulation_datafile = dataset_obj.datafile
        else:
            simulation_datafile = datafile
        
        # Create simulation metadata
        # Store the first year for backward compatibility, but data contains all years
        simulation = SimulationMetadata(
            id=sim_id,
            country=country.lower(),
            year=years_to_process[0] if years_to_process else datetime.now().year,
            file_size_mb=file_size_mb,
            dataset=dataset,
            scenario=scenario,
            model_version=get_model_version(country),
            status=SimulationStatus.COMPLETED,
            completed_at=datetime.now(),
            tags=tags,
            datafile=simulation_datafile
        )
        session.add(simulation)
        session.commit()
        session.refresh(simulation)
        # Attach storage backend for get_data() method
        simulation._storage = self.storage
        session.expunge(simulation)
        return simulation
    
    def get_simulation_metadata(
        self,
        session: Session,
        scenario: str,
        dataset: str,
        country: str = None,
        year: int = None,
    ) -> Optional[SimulationMetadata]:
        """Retrieve simulation metadata.
        
        Args:
            session: Database session
            scenario: Name of the scenario
            dataset: Name of the dataset
            country: Country code (uses default if not specified)
            year: Year of simulation (optional filter)
            
        Returns:
            SimulationMetadata object with get_data() method, or None if not found
        """
        country = country or self.default_country
        if not country:
            raise ValueError("Country must be specified or set as default")
        
        query = session.query(SimulationMetadata).filter_by(
            scenario=scenario,
            dataset=dataset,
            country=country.lower(),
            status=SimulationStatus.COMPLETED
        )
        
        if year:
            query = query.filter_by(year=year)
        
        # Get most recent simulation matching criteria
        simulation = query.order_by(SimulationMetadata.created_at.desc()).first()
        
        if simulation:
            # Store storage backend reference for get_data() method
            simulation._storage = self.storage
            session.expunge(simulation)
        
        return simulation
    
    def get_simulation(
        self,
        session: Session,
        scenario: str,
        dataset: str,
        country: str = None,
        year: int = None,
    ) -> Optional[Union[UKModelOutput, USModelOutput]]:
        """Retrieve simulation results (legacy method, returns model output directly).
        
        Args:
            session: Database session
            scenario: Name of the scenario
            dataset: Name of the dataset
            country: Country code (uses default if not specified)
            year: Year of simulation (optional filter)
            
        Returns:
            UKModelOutput or USModelOutput object, or None if not found
        """
        simulation = self.get_simulation_metadata(session, scenario, dataset, country, year)
        
        if not simulation:
            return None
        
        # Load and return the data directly
        data = self.storage.load_simulation(
            sim_id=simulation.id,
            country=simulation.country,
            scenario=scenario,
            dataset=dataset,
            year=simulation.year
        )
        
        if data is None:
            return None
        
        # Return the appropriate model output type
        if simulation.country.lower() == 'uk':
            return UKModelOutput.from_tables(data)
        elif simulation.country.lower() == 'us':
            return USModelOutput.from_tables(data)
        else:
            raise ValueError(f"Unsupported country: {simulation.country}")
    
    def _extract_all_variables(self, simulation: Any, years: List[int]) -> Dict[int, Dict[str, Dict[str, Any]]]:
        """Extract all calculated variables from simulation, organized by year and entity.
        
        Returns:
            Dictionary with structure: {year: {entity: {variable: values}}}
        """
        result = {}
        
        # Get all entities in the simulation
        entities = simulation.tax_benefit_system.entities
        
        for year in years:
            year_data = {}
            
            for entity_key, entity in entities.items():
                entity_data = {}
                
                # Get all variables for this entity
                for variable_name, variable in simulation.tax_benefit_system.variables.items():
                    if variable.entity.key == entity_key:
                        try:
                            # Try to calculate the variable for this year
                            values = simulation.calculate(variable_name, year)
                            entity_data[variable_name] = values
                        except:
                            # Variable not calculable for this year/scenario
                            pass
                
                if entity_data:
                    year_data[entity_key] = entity_data
            
            result[year] = year_data
        
        return result
    
    def _extract_year_data(self, simulation: Any, year: int) -> Dict[str, Any]:
        """Extract basic data for a specific year from simulation.
        
        Returns:
            Dictionary with entity-level data for the year
        """
        result = {}
        
        # Get key variables for each entity
        entities = simulation.tax_benefit_system.entities
        
        for entity_key, entity in entities.items():
            entity_data = {}
            
            # Define key variables to extract per entity type
            if entity_key == 'household':
                key_vars = ['household_net_income', 'household_benefits', 'household_tax']
            elif entity_key == 'person':
                key_vars = ['employment_income', 'total_income', 'age']
            else:
                key_vars = []
            
            for var_name in key_vars:
                try:
                    values = simulation.calculate(var_name, year)
                    entity_data[var_name] = values
                except:
                    pass
            
            if entity_data:
                result[entity_key] = entity_data
        
        return result
    
    def list_simulations(
        self,
        session: Session,
        country: str = None,
        scenario: str = None,
        dataset: str = None,
        year: int = None,
        tags: List[str] = None
    ) -> List[SimulationMetadata]:
        """List simulations matching criteria.
        
        Args:
            session: Database session
            country: Filter by country
            scenario: Filter by scenario
            dataset: Filter by dataset
            year: Filter by year
            tags: Filter by tags
            
        Returns:
            List of SimulationMetadata objects
        """
        query = session.query(SimulationMetadata)
        
        if country:
            query = query.filter_by(country=country.lower())
        elif self.default_country:
            query = query.filter_by(country=self.default_country.lower())
        
        if scenario:
            query = query.filter_by(scenario=scenario)
        
        if dataset:
            query = query.filter_by(dataset=dataset)
        
        if year:
            query = query.filter_by(year=year)
        
        if tags:
            # Filter by tags (assuming tags are stored as JSON array)
            for tag in tags:
                query = query.filter(SimulationMetadata.tags.contains(tag))
        
        simulations = query.order_by(SimulationMetadata.created_at.desc()).all()
        for sim in simulations:
            session.expunge(sim)
        return simulations