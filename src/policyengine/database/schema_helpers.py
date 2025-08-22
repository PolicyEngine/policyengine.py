"""Helper functions to extract schema from country packages."""

from typing import Dict, List, Any
import importlib
from sqlalchemy import Column, String, Integer, Float, Boolean, Text


def get_country_schema_from_package(country: str) -> Dict[str, List[Dict[str, Any]]]:
    """Extract entity and variable definitions from a country package.
    
    Args:
        country: Country code (e.g., 'uk', 'us')
        
    Returns:
        Dictionary mapping entity names to their variable definitions
    """
    # Import the country package
    try:
        if country == 'uk':
            from policyengine_uk import CountryTaxBenefitSystem as TaxBenefitSystem
        elif country == 'us':
            from policyengine_us import CountryTaxBenefitSystem as TaxBenefitSystem
        else:
            # Try dynamic import
            module = importlib.import_module(f'policyengine_{country}')
            TaxBenefitSystem = module.CountryTaxBenefitSystem
    except ImportError:
        raise ValueError(f"Country package 'policyengine_{country}' not found")
    
    # Initialize the system
    system = TaxBenefitSystem()
    
    # Get all entities
    entities = {}
    for entity in system.entities:
        entities[entity.key] = entity
    
    # Group variables by entity
    entity_variables = {entity_key: [] for entity_key in entities.keys()}
    
    for var_name, variable_class in system.variables.items():
        # Get the entity this variable belongs to
        entity_key = variable_class.entity.key
        
        # Skip if entity not in our list (shouldn't happen)
        if entity_key not in entity_variables:
            continue
        
        # Determine data type from value_type
        value_type = getattr(variable_class, 'value_type', float)
        if value_type == int:
            data_type = 'integer'
        elif value_type == float:
            data_type = 'float'
        elif value_type == bool:
            data_type = 'boolean'
        elif value_type == str:
            data_type = 'string'
        else:
            # Default to float for numeric types
            data_type = 'float'
        
        # Add variable definition
        entity_variables[entity_key].append({
            'name': var_name,
            'data_type': data_type,
            'is_nullable': True,  # Most variables are nullable
            'default_value': None
        })
    
    # Add essential ID and weight columns for each entity
    for entity_key in entity_variables:
        # Add ID column at the beginning
        entity_variables[entity_key].insert(0, {
            'name': f'{entity_key}_id',
            'data_type': 'string',
            'is_nullable': False,
            'default_value': None
        })
        
        # Add weight column
        entity_variables[entity_key].append({
            'name': 'weight',
            'data_type': 'float',
            'is_nullable': False,
            'default_value': 1.0
        })
    
    return entity_variables


def create_columns_from_country_schema(country: str, entity_name: str) -> Dict[str, Column]:
    """Create SQLAlchemy columns for a specific entity from country package.
    
    Args:
        country: Country code (e.g., 'uk', 'us')
        entity_name: Entity name (e.g., 'person', 'household')
        
    Returns:
        Dictionary mapping column names to SQLAlchemy Column objects
    """
    schema = get_country_schema_from_package(country)
    
    if entity_name not in schema:
        raise ValueError(f"Entity '{entity_name}' not found in {country} schema")
    
    variables = schema[entity_name]
    columns = {}
    
    for var_def in variables:
        col_name = var_def['name']
        data_type = var_def['data_type']
        is_nullable = var_def.get('is_nullable', True)
        default_value = var_def.get('default_value')
        
        # Map data types to SQLAlchemy types
        if data_type == 'string':
            col_type = String
        elif data_type == 'integer':
            col_type = Integer
        elif data_type == 'float':
            col_type = Float
        elif data_type == 'boolean':
            col_type = Boolean
        elif data_type == 'text':
            col_type = Text
        else:
            col_type = Float  # Default to float
        
        # Check if this is the ID column
        is_primary = col_name == f'{entity_name}_id'
        
        columns[col_name] = Column(
            col_name,
            col_type,
            primary_key=is_primary,
            nullable=is_nullable and not is_primary,
            default=default_value
        )
    
    return columns


def populate_schema_tables(db, country: str):
    """Populate the EntityType and Variable tables for a country.
    
    This should be called when setting up a new country in the database.
    
    Args:
        db: Database instance
        country: Country code (e.g., 'uk', 'us')
    """
    from .models import EntityTypeDataModel, VariableDataModel
    
    schema = get_country_schema_from_package(country)
    
    with db.get_session() as session:
        for entity_name, variables in schema.items():
            # Check if entity type already exists
            existing = session.query(EntityTypeDataModel).filter_by(
                country=country, name=entity_name
            ).first()
            
            if not existing:
                # Create entity type record
                table_name = f"{country}_{entity_name}"
                entity_type = EntityTypeDataModel(
                    country=country,
                    name=entity_name,
                    table_name=table_name
                )
                session.add(entity_type)
                session.flush()
                
                # Create variable records
                for var_def in variables:
                    variable = VariableDataModel(
                        entity_type_id=entity_type.id,
                        name=var_def['name'],
                        data_type=var_def['data_type'],
                        is_nullable=var_def.get('is_nullable', True),
                        default_value=var_def.get('default_value')
                    )
                    session.add(variable)
                
                # Create the actual table
                columns = create_columns_from_country_schema(country, entity_name)
                db.create_country_table(table_name, columns)
        
        session.commit()


def initialize_country_tables(db, country: str):
    """Initialize all tables for a country from its package.
    
    Args:
        db: Database instance
        country: Country code (e.g., 'uk', 'us')
    """
    schema = get_country_schema_from_package(country)
    
    for entity_name in schema:
        table_name = f"{country}_{entity_name}"
        columns = create_columns_from_country_schema(country, entity_name)
        db.create_country_table(table_name, columns)
    
    # Populate schema tracking tables
    populate_schema_tables(db, country)