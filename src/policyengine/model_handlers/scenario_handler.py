"""Storage-agnostic scenario handler.

This module provides business logic for working with scenarios using
Pydantic models, independent of storage implementation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from ..data_models import ScenarioModel, ParameterChangeModel


class ScenarioHandler:
    """Handles scenario operations using Pydantic models."""
    
    @staticmethod
    def create_scenario(
        name: str,
        country: str,
        parameter_changes: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        parent_scenario_name: Optional[str] = None,
        model_version: Optional[str] = None,
    ) -> ScenarioModel:
        """Create a new scenario from parameters.
        
        Args:
            name: Unique scenario name
            country: Country code
            parameter_changes: Dictionary of parameter changes
            description: Human-readable description
            parent_scenario_name: Name of parent scenario if this is a modification
            model_version: Model version string
            
        Returns:
            ScenarioModel instance
        """
        # Process parameter changes into ParameterChangeModel objects
        change_models = []
        if parameter_changes:
            change_models = ScenarioHandler._parse_parameter_changes(parameter_changes)
        
        return ScenarioModel(
            name=name,
            country=country.lower() if country else "default",
            description=description,
            parameter_changes=change_models,
            parent_scenario_name=parent_scenario_name,
            model_version=model_version
        )
    
    @staticmethod
    def _parse_parameter_changes(
        parameter_changes: Dict[str, Any]
    ) -> List[ParameterChangeModel]:
        """Parse parameter changes from various formats.
        
        Args:
            parameter_changes: Dictionary of parameter changes
            
        Returns:
            List of ParameterChangeModel objects
        """
        change_models = []
        
        for param_name, value in parameter_changes.items():
            if isinstance(value, dict):
                # Period-based changes like {"2024-01-01": 1000, "2025-01-01": 1100}
                for period_str, period_value in value.items():
                    start_date, end_date = ScenarioHandler._parse_period_string(period_str)
                    change_models.append(
                        ParameterChangeModel(
                            parameter_name=param_name,
                            start_date=start_date,
                            end_date=end_date,
                            value=period_value,
                            order_index=len(change_models)
                        )
                    )
            else:
                # Simple value change
                change_models.append(
                    ParameterChangeModel(
                        parameter_name=param_name,
                        start_date=datetime.now(),
                        value=value,
                        order_index=len(change_models)
                    )
                )
        
        return change_models
    
    @staticmethod
    def _parse_period_string(period_str: str) -> tuple[datetime, Optional[datetime]]:
        """Parse period string into start and end dates.
        
        Args:
            period_str: Period string like "2024-01-01" or "2024-01-01:2024-12-31"
            
        Returns:
            Tuple of (start_date, end_date)
        """
        if ":" in period_str:
            start_str, end_str = period_str.split(":")
            start_date = datetime.fromisoformat(start_str)
            end_date = datetime.fromisoformat(end_str)
        else:
            start_date = datetime.fromisoformat(period_str)
            end_date = None
        
        return start_date, end_date
    
    @staticmethod
    def merge_scenarios(
        base_scenario: ScenarioModel,
        override_scenario: ScenarioModel,
        new_name: Optional[str] = None,
        new_description: Optional[str] = None
    ) -> ScenarioModel:
        """Merge two scenarios, with override taking precedence.
        
        Args:
            base_scenario: Base scenario
            override_scenario: Scenario with overrides
            new_name: Name for merged scenario
            new_description: Description for merged scenario
            
        Returns:
            Merged ScenarioModel
        """
        # Combine parameter changes
        merged_changes = {}
        
        # Start with base scenario changes
        for change in base_scenario.parameter_changes:
            key = (change.parameter_name, change.start_date)
            merged_changes[key] = change
        
        # Override with new scenario changes
        for change in override_scenario.parameter_changes:
            key = (change.parameter_name, change.start_date)
            merged_changes[key] = change
        
        # Sort by order index and recreate list
        sorted_changes = sorted(merged_changes.values(), key=lambda x: x.order_index)
        
        return ScenarioModel(
            name=new_name or f"{base_scenario.name}_merged_{override_scenario.name}",
            country=override_scenario.country or base_scenario.country,
            description=new_description or f"Merged from {base_scenario.name} and {override_scenario.name}",
            parameter_changes=sorted_changes,
            parent_scenario_name=base_scenario.name,
            model_version=override_scenario.model_version or base_scenario.model_version
        )
    
    @staticmethod
    def get_current_law_scenario(country: str) -> ScenarioModel:
        """Create a current law scenario (no changes).
        
        Args:
            country: Country code
            
        Returns:
            Current law ScenarioModel
        """
        return ScenarioModel(
            name="current_law",
            country=country.lower(),
            description=f"Current law baseline for {country.upper()}",
            parameter_changes=[],
            model_version=None
        )
    
    @staticmethod
    def validate_scenario(scenario: ScenarioModel) -> bool:
        """Validate a scenario model.
        
        Args:
            scenario: ScenarioModel to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        if not scenario.name:
            raise ValueError("Scenario must have a name")
        
        if not scenario.country:
            raise ValueError("Scenario must have a country")
        
        # Validate parameter changes
        for change in scenario.parameter_changes:
            if not change.parameter_name:
                raise ValueError("Parameter change must have a parameter name")
            
            if change.end_date and change.end_date <= change.start_date:
                raise ValueError(f"End date must be after start date for {change.parameter_name}")
        
        return True
    
    @staticmethod
    def scenario_to_dict(scenario: ScenarioModel) -> Dict[str, Any]:
        """Convert scenario to dictionary for serialization.
        
        Args:
            scenario: ScenarioModel to convert
            
        Returns:
            Dictionary representation
        """
        return {
            "name": scenario.name,
            "country": scenario.country,
            "description": scenario.description,
            "parent_scenario_name": scenario.parent_scenario_name,
            "model_version": scenario.model_version,
            "parameter_changes": [
                {
                    "parameter_name": change.parameter_name,
                    "start_date": change.start_date.isoformat(),
                    "end_date": change.end_date.isoformat() if change.end_date else None,
                    "value": change.value,
                    "description": change.description,
                    "order_index": change.order_index
                }
                for change in scenario.parameter_changes
            ]
        }
    
    @staticmethod
    def scenario_from_dict(data: Dict[str, Any]) -> ScenarioModel:
        """Create scenario from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            ScenarioModel instance
        """
        # Parse parameter changes
        parameter_changes = []
        for change_data in data.get("parameter_changes", []):
            parameter_changes.append(
                ParameterChangeModel(
                    parameter_name=change_data["parameter_name"],
                    start_date=datetime.fromisoformat(change_data["start_date"]),
                    end_date=datetime.fromisoformat(change_data["end_date"]) if change_data.get("end_date") else None,
                    value=change_data["value"],
                    description=change_data.get("description"),
                    order_index=change_data.get("order_index", 0)
                )
            )
        
        return ScenarioModel(
            name=data["name"],
            country=data["country"],
            description=data.get("description"),
            parameter_changes=parameter_changes,
            parent_scenario_name=data.get("parent_scenario_name"),
            model_version=data.get("model_version")
        )