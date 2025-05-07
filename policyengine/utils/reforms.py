from pydantic import (
    RootModel,
    Field,
    field_validator,
)
from typing import Dict, Any
from typing_extensions import Annotated
from policyengine_core.simulations import Simulation


class ParameterChangeValue(RootModel):
    """A value for a parameter change, which can be any primitive type or 'Infinity'/'-Infinity'"""

    # To prevent validation errors, allow all types except containers
    # via field validator
    root: Any

    @field_validator("root", mode="after")
    @classmethod
    def check_type(cls, value: Any) -> Any:
        # Check if the value is not a container type
        if isinstance(value, (dict, list, set, tuple)):
            raise ValueError(
                "ParameterChangeValue must not be a container type (dict, list, set, tuple)"
            )
        return value

    # Convert "Infinity" to "np.inf" and "-Infinity" to "-np.inf"
    @field_validator("root", mode="after")
    @classmethod
    def convert_infinity(cls, value: Any) -> Any:
        if isinstance(value, str):
            if value == "Infinity":
                value = float("inf")
            elif value == "-Infinity":
                value = float("-inf")
        return value


class ParameterChangePeriod(RootModel):
    """A period for a parameter change, which can be a single year or a date range"""

    root: Annotated[
        str,
        Field(
            pattern=r"^\d{4}$|^\d{4}-\d{2}-\d{2}\.\d{4}-\d{2}-\d{2}$",
            description="A single year (YYYY) or a date range (YYYY-MM-DD.YYYY-MM-DD)",
        ),
    ]

    def __hash__(self):
        return hash(self.root)

    def __eq__(self, other):
        if isinstance(other, ParameterChangePeriod):
            return self.root == other.root
        return False


class ParameterChangeDict(RootModel):
    """
    A dict of changes to a parameter, with custom date string as keys
    and various possible value types.

    Keys can be formatted one of two ways:
    1. A single year (e.g., "YYYY")
    2. A date range (e.g., "YYYY-MM-DD.YYYY-MM-DD")
    """

    root: Dict[ParameterChangePeriod, ParameterChangeValue]


class ParametricReform(RootModel):
    """
    A reform that just changes parameter values.

    This is a dict that equates a parameter name to either a single value or a dict of changes.

    """

    root: Dict[str, ParameterChangeValue | ParameterChangeDict]
