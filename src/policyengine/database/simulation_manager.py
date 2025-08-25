"""Simulation management functions."""

import uuid
from datetime import datetime
from typing import Any, Optional, List, Union
from sqlalchemy.orm import Session
from .models import SimulationMetadata, SimulationStatus, ScenarioMetadata, DatasetMetadata, get_model_version
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
        tags: List[str] = None,
    ) -> SimulationMetadata:
        """Store simulation results.
        
        Args:
            session: Database session
            scenario: Name of the scenario used
            simulation: Simulation object from policyengine_core
            dataset: Name of the dataset used (optional, extracted from simulation if not provided)
            country: Country code (uses default if not specified)
            year: Year of simulation
            tags: Optional tags for filtering
            
        Returns:
            Created SimulationMetadata object
        """
        country = country or self.default_country
        if not country:
            raise ValueError("Country must be specified or set as default")
        
        if year is None:
            year = datetime.now().year
        
        # Import the correct country-specific process_simulation
        if country == 'us':
            from ..countries.us import process_us_simulation as process_simulation
        else:
            from ..countries.uk import process_uk_simulation as process_simulation
        
        # Process the simulation to get model output
        model_output = process_simulation(simulation, year).get_tables()
        
        # Verify scenario exists
        scenario_obj = session.query(ScenarioMetadata).filter_by(
            name=scenario,
            country=country.lower()
        ).first()
        
        if not scenario_obj:
            raise ValueError(f"Scenario '{scenario}' not found for country '{country}'")
        
        # Verify dataset if specified
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
                    year=year,
                    model_version=get_model_version(country)
                )
                session.add(dataset_obj)
                session.flush()
        
        # Generate unique ID for simulation
        sim_id = str(uuid.uuid4())
        
        # Save simulation data
        filepath, file_size_mb = self.storage.save_simulation(
            sim_id=sim_id,
            country=country,
            scenario=scenario,
            dataset=dataset,
            year=year,
            data=model_output
        )
        
        # Create simulation metadata
        simulation = SimulationMetadata(
            id=sim_id,
            country=country.lower(),
            year=year,
            file_size_mb=file_size_mb,
            dataset=dataset,
            scenario=scenario,
            model_version=get_model_version(country),
            status=SimulationStatus.COMPLETED,
            completed_at=datetime.now(),
            tags=tags
        )
        session.add(simulation)
        session.commit()
        session.refresh(simulation)
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
        """Retrieve simulation results.
        
        Args:
            session: Database session
            scenario: Name of the scenario
            dataset: Name of the dataset
            country: Country code (uses default if not specified)
            year: Year of simulation (optional filter)
            
        Returns:
            UKModelOutput or USModelOutput object, or None if not found
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
        
        if not simulation:
            return None
        
        # Load simulation data
        data = self.storage.load_simulation(
            sim_id=simulation.id,
            country=country,
            scenario=scenario,
            dataset=dataset,
            year=simulation.year
        )
        
        if data is None:
            return None
        
        # Convert loaded data to appropriate ModelOutput object
        if country.lower() == 'uk':
            return UKModelOutput.from_tables(data)
        elif country.lower() == 'us':
            return USModelOutput.from_tables(data)
        else:
            raise ValueError(f"Unsupported country: {country}")
    
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