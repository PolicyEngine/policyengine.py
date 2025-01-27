import re
from pydantic import RootModel, ValidationError, Field, model_validator
from typing import Dict
from annotated_types import Ge, Le
from typing_extensions import Annotated
from policyengine_core.reforms import Reform as StructuralReform

# Define a constrained year type (1900-2100)
Year = Annotated[int, Field(..., ge=1900, le=2100)]


class YearlyValues(RootModel):
    """Validates yearly values (e.g., {"2025": 0.25})."""

    root: Dict[Year, float]  # Keys auto-converted from strings to integers


class ParametricReform(RootModel):
    """Validates parameter names and their yearly values."""

    root: Dict[str, YearlyValues]

    @model_validator(mode="before")
    def validate_parameter_names(cls, data: dict) -> dict:
        """Ensure parameter names match the allowed format."""
        for param_name in data.keys():
            if not re.match(r"^[a-zA-Z0-9\.]+$", param_name):
                raise ValueError(f"Invalid parameter name: {param_name!r}")
        return data
