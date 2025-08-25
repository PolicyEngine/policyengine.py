"""Scenario management functions."""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from policyengine_core.periods import period as parse_period
from .models import ScenarioMetadata, ParameterMetadata, ParameterChangeMetadata, get_model_version


class ScenarioManager:
    """Manages scenarios and parameter changes."""
    
    def __init__(self, default_country: Optional[str] = None):
        """Initialize scenario manager.
        
        Args:
            default_country: Default country to use when not specified
        """
        self.default_country = default_country
    
    def add_parametric_scenario(
        self,
        session: Session,
        name: str,
        parameter_changes: dict = None,
        country: str = None,
        description: str = None,
    ) -> ScenarioMetadata:
        """Add a parametric scenario with parameter changes.
        
        Args:
            session: Database session
            name: Name of the scenario
            parameter_changes: Dictionary of parameter changes in various formats
            country: Country code (uses default if not specified)
            description: Optional description of the scenario
            
        Returns:
            Created ScenarioMetadata object
        """
        country = country or self.default_country
        if not country:
            raise ValueError("Country must be specified or set as default")
        
        parameter_changes = parameter_changes or {}
        
        # Check if scenario already exists
        existing = session.query(ScenarioMetadata).filter_by(
            name=name,
            country=country.lower()
        ).first()
        
        if existing:
            # Update existing scenario - clear old parameter changes
            existing.model_version = get_model_version(country)
            existing.updated_at = datetime.now()
            session.query(ParameterChangeMetadata).filter_by(
                scenario_id=existing.id
            ).delete()
            scenario = existing
        else:
            # Create new scenario
            scenario = ScenarioMetadata(
                id=str(uuid.uuid4()),
                name=name,
                country=country.lower(),
                model_version=get_model_version(country),
                description=description or f"Parametric reform scenario: {name}"
            )
            session.add(scenario)
            session.flush()
        
        # Process parameter changes
        for param_name, value_spec in parameter_changes.items():
            # Get or create parameter metadata
            param = session.query(ParameterMetadata).filter_by(
                name=param_name,
                country=country.lower()
            ).first()
            
            if not param:
                # Create parameter if it doesn't exist
                param = ParameterMetadata(
                    id=str(uuid.uuid4()),
                    name=param_name,
                    country=country.lower(),
                    data_type=self._infer_data_type(value_spec)
                )
                session.add(param)
                session.flush()
            
            # Parse value specification
            if isinstance(value_spec, dict):
                # Multiple time periods specified
                for period_str, value in value_spec.items():
                    start_date, end_date = self._parse_period_string(period_str)
                    change = ParameterChangeMetadata(
                        id=str(uuid.uuid4()),
                        scenario_id=scenario.id,
                        parameter_id=param.id,
                        start_date=start_date,
                        end_date=end_date,
                        value=value if isinstance(value, (bool, int, float, str)) else json.dumps(value),
                        model_version=get_model_version(country)
                    )
                    session.add(change)
            else:
                # Single value for default period (2000-2100)
                change = ParameterChangeMetadata(
                    id=str(uuid.uuid4()),
                    scenario_id=scenario.id,
                    parameter_id=param.id,
                    start_date=datetime(2000, 1, 1),
                    end_date=datetime(2100, 1, 1),
                    value=value_spec if isinstance(value_spec, (bool, int, float, str)) else json.dumps(value_spec),
                    model_version=get_model_version(country)
                )
                session.add(change)
        
        session.commit()
        session.refresh(scenario)
        # Eagerly load parameter_changes before expunging
        scenario = session.query(ScenarioMetadata).options(
            joinedload(ScenarioMetadata.parameter_changes)
        ).filter_by(id=scenario.id).first()
        # Make the object independent of the session
        session.expunge_all()
        return scenario
    
    def get_scenario(
        self,
        session: Session,
        name: str,
        country: str = None
    ) -> Optional[ScenarioMetadata]:
        """Get a scenario by name and country.
        
        Args:
            session: Database session
            name: Name of the scenario
            country: Country code (uses default if not specified)
            
        Returns:
            ScenarioMetadata object or None if not found
        """
        country = country or self.default_country
        if not country:
            raise ValueError("Country must be specified or set as default")
        
        scenario = session.query(ScenarioMetadata).options(
            joinedload(ScenarioMetadata.parameter_changes)
        ).filter_by(
            name=name,
            country=country.lower()
        ).first()
        
        if scenario:
            session.expunge_all()
        
        return scenario
    
    def _infer_data_type(self, value) -> str:
        """Infer the data type from a value."""
        if isinstance(value, dict):
            # Get first value from dict
            first_val = next(iter(value.values())) if value else None
            if first_val is not None:
                return self._infer_data_type(first_val)
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        return "json"
    
    def _parse_period_string(self, period_str: str) -> tuple[datetime, datetime]:
        """Parse a period string into start and end dates.
        
        Formats:
        - "2000-01-01.2023-01-01" -> explicit date range
        - "year:2026:1" -> uses policyengine_core.periods
        - "2025-01-01" -> single date (end is None)
        """
        if "." in period_str:
            # Date range format
            start_str, end_str = period_str.split(".")
            start_date = datetime.fromisoformat(start_str)
            end_date = datetime.fromisoformat(end_str)
            return start_date, end_date
        elif ":" in period_str:
            # Period notation
            p = parse_period(period_str)
            start_date = datetime.fromisoformat(str(p.start))
            end_date = datetime.fromisoformat(str(p.stop))
            return start_date, end_date
        else:
            # Single date
            start_date = datetime.fromisoformat(period_str)
            return start_date, None