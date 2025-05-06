import re
from pydantic import (
    RootModel,
    ValidationError,
    Field,
    model_validator,
    field_validator,
)
from typing import Dict, Self, Any, TYPE_CHECKING
from typing_extensions import Annotated
from typing import Callable
from policyengine_core.simulations import Simulation


class ParameterChangeDict(RootModel):
    """A dict of changes to a parameter, with custom date string as keys
    and various possible value types."""

    root: Dict[str, Any]

    @model_validator(mode="after")
    def check_keys(self) -> Self:
        for key in self.root.keys():
            # Check if key is YYYY-MM-DD.YYYY-MM-DD
            if not re.match(r"^\d{4}-\d{2}-\d{2}\.\d{4}-\d{2}-\d{2}$", key):
                raise ValueError(f"Invalid date format in key: {key}")
        return self

    # Convert "Infinity" to "np.inf" and "-Infinity" to "-np.inf"
    @field_validator("root", mode="after")
    @classmethod
    def convert_infinity(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        for key, val in value.items():
            if isinstance(val, str):
                if val == "Infinity":
                    value[key] = float("inf")
                elif val == "-Infinity":
                    value[key] = float("-inf")
        return value


class ParametricReform(RootModel):
    """A reform that just changes parameter values."""

    root: Dict[str, ParameterChangeDict]
