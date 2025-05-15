import re
from pydantic import (
    RootModel,
    field_validator,
)
from typing import Dict, Any


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


class ParameterChangeDict(RootModel):
    """
    A dict of changes to a parameter, with custom date string as keys
    and various possible value types.

    Keys can be formatted one of two ways:
    1. A single year (e.g., "YYYY")
    2. A date range (e.g., "YYYY-MM-DD.YYYY-MM-DD")
    """

    root: Dict[str, ParameterChangeValue]

    @field_validator("root", mode="after")
    @classmethod
    def validate_dates(
        cls, value: Dict[str, ParameterChangeValue]
    ) -> Dict[str, ParameterChangeValue]:

        year_keys_re = r"^\d{4}$"
        date_range_keys_re = r"^\d{4}-\d{2}-\d{2}\.\d{4}-\d{2}-\d{2}$"

        for key in value.keys():
            if not re.match(year_keys_re, key) and not re.match(
                date_range_keys_re, key
            ):
                raise ValueError(
                    f"Key '{key}' must be a single year (YYYY) or a date range (YYYY-MM-DD.YYYY-MM-DD)"
                )
        return value


class ParametricReform(RootModel):
    """
    A reform that just changes parameter values.

    This is a dict that equates a parameter name to either a single value or a dict of changes.

    """

    root: Dict[str, ParameterChangeValue | ParameterChangeDict]
