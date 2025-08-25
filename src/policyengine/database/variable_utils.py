"""Utilities for extracting and managing variables from policyengine-core."""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from .models import VariableMetadata, get_model_version
import uuid


def extract_variable_metadata(
    variable,
    country: str
) -> VariableMetadata:
    """Extract metadata from a policyengine-core variable.
    
    Args:
        variable: Variable from policyengine-core
        country: Country code (e.g., 'uk', 'us')
        
    Returns:
        VariableMetadata model instance
    """
    # Determine value type from variable
    value_type = getattr(variable, 'value_type', None)
    if value_type:
        value_type_name = value_type.__name__ if hasattr(value_type, '__name__') else str(value_type)
        if 'float' in value_type_name.lower():
            value_type_str = 'float'
        elif 'int' in value_type_name.lower():
            value_type_str = 'int'
        elif 'bool' in value_type_name.lower():
            value_type_str = 'bool'
        elif 'str' in value_type_name.lower():
            value_type_str = 'string'
        elif 'enum' in value_type_name.lower():
            value_type_str = 'enum'
        else:
            value_type_str = 'float'  # default
    else:
        value_type_str = 'float'
    
    # Extract metadata
    metadata = VariableMetadata(
        id=str(uuid.uuid4()),
        name=variable.name,
        country=country.lower(),
        label=getattr(variable, 'label', None),
        description=getattr(variable, 'documentation', None),
        unit=getattr(variable, 'unit', None),
        value_type=value_type_str,
        entity=variable.entity.key if hasattr(variable, 'entity') else 'unknown',
        definition_period=getattr(variable, 'definition_period', None),
        model_version=get_model_version(country)
    )
    
    return metadata


def import_variables_from_tax_benefit_system(
    session: Session,
    tax_benefit_system,
    country: str
) -> int:
    """Import all variables from a tax benefit system into the database.
    
    Args:
        session: Database session
        tax_benefit_system: PolicyEngine tax benefit system
        country: Country code
        
    Returns:
        Number of variables imported/updated
    """
    count = 0
    current_version = get_model_version(country)
    
    # Get all variables from the tax benefit system
    variables = tax_benefit_system.variables
    
    for variable_name, variable in variables.items():
        # Check if variable already exists
        existing = session.query(VariableMetadata).filter_by(
            name=variable_name,
            country=country.lower()
        ).first()
        
        if existing:
            # Update existing variable's model version and metadata
            existing.label = getattr(variable, 'label', existing.label)
            existing.description = getattr(variable, 'documentation', existing.description)
            existing.unit = getattr(variable, 'unit', existing.unit)
            existing.model_version = current_version
            existing.updated_at = datetime.now()
        else:
            # Create new variable entry
            variable_meta = extract_variable_metadata(variable, country)
            session.add(variable_meta)
            count += 1
    
    session.commit()
    return count