"""Simulation management for PolicyEngine database."""

from typing import Optional, Any, List, Union
import datetime
import pandas as pd
import numpy as np
from .default_variables import get_default_variables


def add_simulation(
    db,
    scenario_name: str,
    simulation: Any,
    source_dataset: str,
    year: Optional[int] = None,
    variables: Optional[Union[str, List[str]]] = "default"
):
    """Add a simulation to the database using pandas for fast insertion.
    
    Args:
        db: Database instance
        scenario_name: Name of the scenario (creates new or overwrites existing)
        simulation: Microsimulation object with calculated data
        source_dataset: ID of the source dataset (creates if not exists)
        year: Year for the simulation (defaults to current year)
        variables: Variables to calculate and store. Options:
            - "default": Use default variable set for the country (DEFAULT_VARIABLES_UK or DEFAULT_VARIABLES_US)
            - List[str]: Custom list of variable names to calculate
    """
    from .models import SourceDatasetDataModel, ScenarioDataModel, PopulationDataModel
    
    # Default year to current year
    if year is None:
        year = datetime.datetime.now().year
    
    # Get country from simulation
    country = simulation.tax_benefit_system.parameters.metadata.get('country', 'uk')
    if country == 'GB':
        country = 'uk'
    elif country == 'US':
        country = 'us'
    country = country.lower()
    
    with db.get_session() as session:
        # Check if source dataset exists, create if not
        source_dataset_obj = session.query(SourceDatasetDataModel).filter_by(
            name=source_dataset
        ).first()
        
        if not source_dataset_obj:
            # Auto-create source dataset
            source_dataset_obj = SourceDatasetDataModel(
                name=source_dataset,
                year=year,
                description=f"Auto-created dataset for {scenario_name}"
            )
            session.add(source_dataset_obj)
            session.flush()
            print(f"Created source dataset '{source_dataset}'")
        
        # Check if scenario exists
        scenario = session.query(ScenarioDataModel).filter_by(
            name=scenario_name,
            country=country
        ).first()
        
        if scenario:
            # Delete existing scenario and its data (cascade will handle related records)
            session.delete(scenario)
            session.flush()
        
        # Create new scenario
        scenario = ScenarioDataModel(
            name=scenario_name,
            country=country,
            description=f"Simulation from {source_dataset}"
        )
        session.add(scenario)
        session.flush()
        
        # Create population
        population = PopulationDataModel(
            name=f"{scenario_name}_population",
            description=f"Population for {scenario_name}",
            country=country,
            source_dataset_id=source_dataset_obj.id
        )
        session.add(population)
        session.flush()
        
        # Get all entities from the simulation
        entities = simulation.tax_benefit_system.entities
        
        # Process each entity
        for entity in entities:
            entity_key = entity.key
            table_name = f"{country}_{entity_key}"
            
            # Get the table
            table = db.get_country_table(table_name)
            if table is None:
                # Create table if it doesn't exist
                db._initialize_country(country)
                table = db.get_country_table(table_name)
            
            # Get entity population
            entity_population = getattr(simulation, entity_key)
            entity_ids = entity_population.ids
            num_entities = len(entity_ids)
            
            if num_entities == 0:
                continue
                
            print(f"Processing {entity_key} with {num_entities} records...")
            
            # Start with IDs and weights
            df_data = {
                'id': [f"{population.id}_{entity_key}_{i}" for i in range(num_entities)],
                f'{entity_key}_id': entity_ids
            }
            
            # Add weights
            weights = getattr(entity_population, 'weights', None)
            if weights is not None:
                df_data['weight'] = weights
            else:
                df_data['weight'] = np.ones(num_entities, dtype=np.float32)
            
            # Get variables to calculate based on configuration
            if isinstance(variables, str) and variables == "default":
                # Use default variable list for the country
                variable_names = get_default_variables(country)
            elif isinstance(variables, list):
                # Custom variable list provided
                variable_names = variables
            else:
                # Fall back to default
                variable_names = get_default_variables(country)
            
            # Filter to only variables that exist for this entity
            all_entity_variables = {
                var.name: var for _, var in simulation.tax_benefit_system.variables.items()
                if var.entity.key == entity_key
            }
            
            # Get variables that exist for this entity
            variables_to_calc = []
            for var_name in variable_names:
                if var_name in all_entity_variables:
                    variables_to_calc.append(all_entity_variables[var_name])
            
            # Always ensure we have weights
            essential = [f"{entity_key}_weight", "weight"]
            for var_name in essential:
                if var_name in all_entity_variables and var_name not in [v.name for v in variables_to_calc]:
                    variables_to_calc.append(all_entity_variables[var_name])
            
            if len(variables_to_calc) == 0:
                print(f"  No valid variables found for {entity_key}, skipping...")
                continue
            
            print(f"  Using {len(variables_to_calc)} variables from default set")
            
            # Calculate variables
            print(f"  Calculating {len(variables_to_calc)} variables...")
            calculated = 0
            
            for i, var in enumerate(variables_to_calc):
                try:
                    values = simulation.calculate(var.name, period=year)
                    df_data[var.name] = values
                    calculated += 1
                    
                    if (i + 1) % 20 == 0:
                        print(f"    Progress: {i + 1}/{len(variables_to_calc)} variables...")
                except Exception:
                    # Skip variables that can't be calculated
                    continue
            
            print(f"  Calculated {calculated} variables successfully")
            
            # Create DataFrame
            df = pd.DataFrame(df_data)
            
            # Insert using pandas to_sql - this is highly optimized
            print(f"  Inserting {len(df)} records using pandas...")
            
            start_time = datetime.datetime.now()
            
            # Calculate safe chunksize based on database type and number of columns
            num_columns = len(df.columns)
            
            if db.is_postgres:
                # PostgreSQL can handle many more variables
                safe_chunksize = 10000
            else:
                # SQLite has a limit of 999 variables per query
                safe_chunksize = min(900 // num_columns, 10000)  # Leave some margin
                
                if safe_chunksize < 1:
                    # Too many columns for a single insert, need to reduce chunksize to 1
                    print(f"    Warning: {num_columns} columns requires row-by-row insertion")
                    safe_chunksize = 1
            
            # Use to_sql with safe chunksize
            df.to_sql(
                name=table_name,
                con=db.engine,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=safe_chunksize
            )
            
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            print(f"  Inserted {len(df)} records in {elapsed:.1f} seconds")
        
        # Create simulation record
        from .models import SimulationDataModel
        simulation_record = SimulationDataModel(
            scenario_id=scenario.id,
            country=country,
            population_id=population.id,
            year=year
        )
        session.add(simulation_record)
        
        session.commit()
        
        print(f"Successfully added simulation '{scenario_name}' to database with {variables} variable set")


def create_source_dataset(
    db,
    name: str,
    year: int,
    description: Optional[str] = None
):
    """Create a source dataset entry.
    
    Args:
        db: Database instance
        name: Name/ID of the source dataset (e.g., 'frs_2023_24')
        year: Year of the dataset
        description: Optional description
    """
    from .models import SourceDatasetDataModel
    
    with db.get_session() as session:
        # Check if already exists
        existing = session.query(SourceDatasetDataModel).filter_by(name=name).first()
        if existing:
            print(f"Source dataset '{name}' already exists")
            return
        
        # Create new source dataset
        source_dataset = SourceDatasetDataModel(
            name=name,
            year=year,
            description=description or f"Source dataset for year {year}"
        )
        session.add(source_dataset)
        session.commit()
        
        print(f"Created source dataset '{name}'")