"""Dynamic schema generation from tax-benefit models."""

from typing import Type, Dict, Any, List, Optional
from pydantic import Field, create_model
from ..models.base import BaseEntity
import importlib
import inspect


def get_entity_variables(tax_benefit_system, entity_key: str) -> List[Any]:
    """Get all variables for a specific entity from the tax benefit system."""
    variables = []
    
    for variable_name, variable_class in tax_benefit_system.variables.items():
        # Get the variable instance
        if hasattr(variable_class, 'entity'):
            # Check if this variable belongs to the entity
            if hasattr(variable_class.entity, 'key') and variable_class.entity.key == entity_key:
                variables.append((variable_name, variable_class))
    
    return variables


def python_type_from_variable(variable_class) -> type:
    """Convert PolicyEngine variable type to Python type."""
    if hasattr(variable_class, 'value_type'):
        value_type = variable_class.value_type
        if value_type == float:
            return float
        elif value_type == int:
            return int
        elif value_type == bool:
            return bool
        elif value_type == str:
            return str
    return float  # Default to float for numeric values


def create_field_from_variable(variable_class) -> Any:
    """Create a Pydantic field from a PolicyEngine variable."""
    python_type = python_type_from_variable(variable_class)
    
    # Get description from label or documentation
    description = ""
    if hasattr(variable_class, 'label'):
        description = variable_class.label
    elif hasattr(variable_class, 'documentation'):
        description = variable_class.documentation
    
    # Default value based on type
    default = None
    if python_type == float:
        default = 0.0
    elif python_type == int:
        default = 0
    elif python_type == bool:
        default = False
    elif python_type == str:
        default = ""
    
    # Check if it's a required field (input variables)
    is_input = getattr(variable_class, 'is_input_variable', lambda: False)()
    
    if is_input:
        return (Optional[python_type], Field(default, description=description))
    else:
        return (Optional[python_type], Field(None, description=description))


def create_dynamic_entity(
    entity_name: str,
    entity_key: str,
    tax_benefit_system: Any,
) -> Type[BaseEntity]:
    """
    Create a dynamic entity class from a tax-benefit system.
    
    Args:
        entity_name: Name for the Pydantic model class
        entity_key: Key of the entity in the tax-benefit system
        tax_benefit_system: The tax-benefit system instance
        include_patterns: List of variable name patterns to include
        exclude_patterns: List of variable name patterns to exclude
    
    Returns:
        A Pydantic model class inheriting from BaseEntity
    """
    # Get variables for this entity
    variables = get_entity_variables(tax_benefit_system, entity_key)
    
    # Build field dictionary
    fields = {}
    
    for variable_name, variable_class in variables:
        try:
            fields[variable_name] = create_field_from_variable(variable_class)
        except Exception:
            # Skip variables that can't be converted
            continue
    
    # Create the dynamic model
    model = create_model(
        entity_name,
        __base__=BaseEntity,
        **fields
    )
    
    return model


def generate_entity_schemas(country: str) -> Dict[str, Type[BaseEntity]]:
    """
    Generate entity schemas for a country.
    
    Args:
        country: Country code ('uk' or 'us')
    
    Returns:
        Dictionary mapping entity names to Pydantic model classes
    """
    schemas = {}
    
    if country.lower() == "uk":
        from policyengine_uk import CountryTaxBenefitSystem
        system = CountryTaxBenefitSystem()
    elif country.lower() == "us":
        from policyengine_us import CountryTaxBenefitSystem
        system = CountryTaxBenefitSystem()
    else:
        raise ValueError(f"Unknown country code: {country}")

    entities = [entity.key for entity in system.entities]

    for entity in entities:
        schemas[entity.capitalize()] = create_dynamic_entity(
            f"{country.upper()}{entity.capitalize()}",
            entity,
            system,
        )
    
    return schemas