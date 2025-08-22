"""Scenario model for policy simulations."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid
import json


class Reform(BaseModel):
    """Represents a parametric reform."""
    
    parameter: str = Field(..., description="Parameter path to modify")
    value: Any = Field(..., description="New value for the parameter")
    period: Optional[str] = Field(None, description="Period for the reform (e.g., '2024')")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_none=True)


class Scenario(BaseModel):
    """Represents a policy scenario with optional reforms."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Name of the scenario")
    country: str = Field(..., description="Country code")
    description: Optional[str] = Field(None, description="Scenario description")
    reforms: List[Reform] = Field(
        default_factory=list,
        description="List of parametric reforms"
    )
    reform_json: Optional[Dict[str, Any]] = Field(
        None,
        description="Full reform specification in JSON format"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @validator("country")
    def validate_country(cls, v):
        """Validate country code."""
        valid_countries = ["uk", "us"]  # Add more as needed
        if v.lower() not in valid_countries:
            raise ValueError(f"Country must be one of {valid_countries}")
        return v.lower()
    
    def add_reform(self, parameter: str, value: Any, period: Optional[str] = None) -> None:
        """Add a reform to the scenario."""
        reform = Reform(parameter=parameter, value=value, period=period)
        self.reforms.append(reform)
        self.updated_at = datetime.now()
    
    def get_reform_dict(self) -> Dict[str, Any]:
        """Get reforms as a dictionary suitable for PolicyEngine models."""
        if self.reform_json:
            return self.reform_json
        
        reform_dict = {}
        for reform in self.reforms:
            if reform.period:
                key = f"{reform.parameter}.{reform.period}"
            else:
                key = reform.parameter
            reform_dict[key] = reform.value
        return reform_dict
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "description": self.description,
            "baseline": self.baseline,
            "reforms": [r.to_dict() for r in self.reforms],
            "reform_json": self.reform_json,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def summary(self) -> str:
        """Get a summary of the scenario."""
        reform_count = len(self.reforms)
        return (
            f"Scenario '{self.name}' for {self.country.upper()}: "
            f"{reform_count} reforms"
        )