"""Utilities for extracting and managing parameters from policyengine-core."""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from sqlalchemy.orm import Session
from policyengine_core.parameters import Parameter, ParameterNode
from policyengine_core.simulations import Simulation
from .models import (
    ParameterMetadata,
    ParameterChangeMetadata,
    ScenarioMetadata,
    Base
)
import json
import uuid


def extract_parameter_metadata(
    param: Union[Parameter, ParameterNode],
    country: str,
    parent_id: Optional[str] = None
) -> ParameterMetadata:
    """Extract metadata from a policyengine-core parameter.
    
    Args:
        param: Parameter or ParameterNode from policyengine-core
        country: Country code (e.g., 'uk', 'us')
        parent_id: ID of parent parameter if this is a child
        
    Returns:
        ParameterMetadata model instance
    """
    # Determine data type
    if isinstance(param, ParameterNode):
        data_type = "node"
    elif hasattr(param, 'values_list') and param.values_list:
        # Infer type from first value
        first_value = param.values_list[0].value
        if isinstance(first_value, bool):
            data_type = "bool"
        elif isinstance(first_value, int) and not isinstance(first_value, bool):
            data_type = "int"
        elif isinstance(first_value, float):
            data_type = "float"
        elif isinstance(first_value, str):
            data_type = "string"
        else:
            data_type = "json"
    else:
        data_type = "unknown"
    
    # Extract metadata
    metadata = ParameterMetadata(
        id=str(uuid.uuid4()),
        name=param.name,
        country=country,
        parent_id=parent_id,
        label=getattr(param, 'description', None),
        description=getattr(param, 'documentation', None),
        unit=getattr(param.metadata, 'unit', None) if hasattr(param, 'metadata') else None,
        data_type=data_type
    )
    
    return metadata


def extract_parameter_changes(
    param: Parameter,
    parameter_id: str,
    scenario_id: str
) -> List[ParameterChangeMetadata]:
    """Extract parameter changes from a policyengine-core parameter.
    
    Args:
        param: Parameter from policyengine-core
        parameter_id: ID of the parameter in database
        scenario_id: ID of the scenario these changes belong to
        
    Returns:
        List of ParameterChangeMetadata instances
    """
    changes = []
    
    if not hasattr(param, 'values_list'):
        return changes
    
    for idx, value_at_instant in enumerate(param.values_list):
        # Parse the instant string to get date
        instant_str = value_at_instant.instant_str
        if instant_str:
            try:
                # Parse date string (format: 'YYYY-MM-DD')
                start_date = datetime.strptime(instant_str, '%Y-%m-%d')
            except ValueError:
                # Try alternative formats
                try:
                    start_date = datetime.fromisoformat(instant_str)
                except:
                    continue
        else:
            continue
        
        # Determine end date (next value's start date or None)
        end_date = None
        if idx > 0:  # Not the most recent value
            prev_instant_str = param.values_list[idx - 1].instant_str
            if prev_instant_str:
                try:
                    end_date = datetime.strptime(prev_instant_str, '%Y-%m-%d')
                except:
                    pass
        
        # Create change record
        change = ParameterChangeMetadata(
            id=str(uuid.uuid4()),
            scenario_id=scenario_id,
            parameter_id=parameter_id,
            start_date=start_date,
            end_date=end_date,
            value=json.dumps(value_at_instant.value) if not isinstance(value_at_instant.value, (bool, int, float, str)) else value_at_instant.value,
            order_index=len(param.values_list) - idx - 1  # Most recent first
        )
        changes.append(change)
    
    return changes


def import_parameters_from_tax_benefit_system(
    session: Session,
    tax_benefit_system,
    country: str,
    scenario_name: str = "current_law",
    scenario_description: str = "Current law parameters"
) -> ScenarioMetadata:
    """Import all parameters from a tax benefit system into the database.
    
    Args:
        session: Database session
        tax_benefit_system: PolicyEngine tax benefit system
        country: Country code
        scenario_name: Name for the scenario
        scenario_description: Description for the scenario
        
    Returns:
        Created scenario with parameters
    """
    # Create or get scenario
    scenario = session.query(ScenarioMetadata).filter_by(
        name=scenario_name,
        country=country
    ).first()
    
    if not scenario:
        scenario = ScenarioMetadata(
            id=str(uuid.uuid4()),
            name=scenario_name,
            country=country,
            description=scenario_description
        )
        session.add(scenario)
        session.flush()
    
    # Track parameters by name to avoid duplicates
    param_map = {}
    
    # Process parameter tree recursively
    def process_parameter_tree(node, parent_id=None):
        """Recursively process parameter tree."""
        
        if isinstance(node, ParameterNode):
            # Create parameter for node
            param_meta = extract_parameter_metadata(node, country, parent_id)
            
            # Check if parameter already exists
            existing = session.query(ParameterMetadata).filter_by(
                name=param_meta.name,
                country=country
            ).first()
            
            if not existing:
                session.add(param_meta)
                session.flush()
                param_id = param_meta.id
            else:
                param_id = existing.id
            
            param_map[node.name] = param_id
            
            # Process children
            for _, child in node.children.items():
                process_parameter_tree(child, param_id)
                
        elif isinstance(node, Parameter):
            # Create parameter metadata
            param_meta = extract_parameter_metadata(node, country, parent_id)
            
            # Check if parameter already exists
            existing = session.query(ParameterMetadata).filter_by(
                name=param_meta.name,
                country=country
            ).first()
            
            if not existing:
                session.add(param_meta)
                session.flush()
                param_id = param_meta.id
            else:
                param_id = existing.id
            
            param_map[node.name] = param_id
            
            # Extract and add parameter changes
            changes = extract_parameter_changes(node, param_id, scenario.id)
            for change in changes:
                # Check if change already exists
                existing_change = session.query(ParameterChangeMetadata).filter_by(
                    scenario_id=scenario.id,
                    parameter_id=param_id,
                    start_date=change.start_date
                ).first()
                
                if not existing_change:
                    session.add(change)
    
    # Start processing from root
    params = tax_benefit_system.parameters
    process_parameter_tree(params)
    
    session.commit()
    return scenario


def get_parameter_value_at_instant(
    session: Session,
    parameter_name: str,
    scenario_id: str,
    instant: datetime
) -> Any:
    """Get the value of a parameter at a specific instant.
    
    Args:
        session: Database session
        parameter_name: Name of the parameter
        scenario_id: ID of the scenario
        instant: Date to get value for
        
    Returns:
        Parameter value at the instant, or None if not found
    """
    # Get parameter
    param = session.query(ParameterMetadata).filter_by(name=parameter_name).first()
    if not param:
        return None
    
    # Find applicable change
    change = session.query(ParameterChangeMetadata).filter(
        ParameterChangeMetadata.scenario_id == scenario_id,
        ParameterChangeMetadata.parameter_id == param.id,
        ParameterChangeMetadata.start_date <= instant
    ).filter(
        (ParameterChangeMetadata.end_date.is_(None)) | 
        (ParameterChangeMetadata.end_date > instant)
    ).order_by(
        ParameterChangeMetadata.start_date.desc()
    ).first()
    
    if change:
        # Parse JSON value if needed
        if isinstance(change.value, str) and change.value.startswith('{'):
            return json.loads(change.value)
        return change.value
    
    return None


def apply_parameter_changes_to_simulation(
    simulation: Simulation,
    session: Session,
    scenario_id: str,
) -> None:
    """Apply parameter changes from a scenario to a simulation.
    
    Args:
        simulation: PolicyEngine simulation to modify
        session: Database session
        scenario_id: ID of the scenario with changes
        year: Year to apply changes for
    """
    # Get all parameter changes for the scenario
    changes = session.query(ParameterChangeMetadata).filter_by(
        scenario_id=scenario_id
    ).order_by(
        ParameterChangeMetadata.order_index
    ).all()
    
    # Group changes by parameter
    changes_by_param = {}
    for change in changes:
        param = session.query(ParameterMetadata).filter_by(id=change.parameter_id).first()
        if param:
            if param.name not in changes_by_param:
                changes_by_param[param.name] = []
            changes_by_param[param.name].append(change)
    
    # Apply changes to simulation
    params = simulation.tax_benefit_system.parameters
    
    for param_name, param_changes in changes_by_param.items():
        # Find applicable change for this instant
        parameter: Parameter = params.get_child(param_name)
        
        for param_change in param_changes:
            param_change: ParameterChangeMetadata
            start_instant = param_change.start_date
            end_instant = param_change.end_date
            parameter.update(
                value=param_change.value,
                start=start_instant,
                stop=end_instant
            )
