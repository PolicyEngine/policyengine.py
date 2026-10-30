import datetime
from collections.abc import Mapping
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator

from .tax_benefit_model_version import TaxBenefitModelVersion


class EnumValue(BaseModel):
    """One value an enum variable can take, with the label users see."""

    value: str = Field(
        description="Name stored in household data, such as 'SINGLE'",
    )
    # Pydantic's smart union keeps each declared scalar's own type: True stays
    # True, 1.0 stays 1.0 and None stays None, rather than being converted.
    label: Union[str, int, float, bool, None] = Field(
        description=(
            "Label shown to users, such as 'Single': the value the country "
            "model declares for the member, unchanged, so a member declared "
            "with an integer, number, boolean or None keeps that value"
        ),
    )


class Variable(BaseModel):
    id: str
    name: str
    label: Optional[str] = None
    tax_benefit_model_version: TaxBenefitModelVersion
    entity: str
    description: Optional[str] = None
    data_type: type = None
    possible_values: Optional[list[Any]] = None
    default_value: Any = None
    value_type: Optional[type] = None
    adds: Optional[list[str]] = None
    subtracts: Optional[list[str]] = None
    definition_period: Optional[str] = None
    unit: Optional[str] = None
    quantity_type: Optional[str] = None
    reference: Optional[list[Any]] = None
    defined_for: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    is_period_size_independent: Optional[bool] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_input_variable: Optional[bool] = Field(
        default=None,
        description=(
            "Whether users enter the variable rather than it being calculated: "
            "it has no formula and no adds or subtracts. None when the country "
            "model does not say."
        ),
    )
    hidden_input: Optional[bool] = Field(
        default=None,
        description=(
            "Whether the variable is hidden from lists of inputs. None when the "
            "country model does not say."
        ),
    )
    module_name: Optional[str] = Field(
        default=None,
        description="Module that defines the variable, as the country model names it",
    )
    adds_parameter_path: Optional[str] = Field(
        default=None,
        description=(
            "Path of the parameter whose value lists the variables this one "
            "adds, when the country model names a parameter rather than a "
            "list. adds then holds that parameter's list as of 2025-01-01 only."
        ),
    )
    subtracts_parameter_path: Optional[str] = Field(
        default=None,
        description=(
            "Path of the parameter whose value lists the variables this one "
            "subtracts, when the country model names a parameter rather than a "
            "list. subtracts then holds that parameter's list as of 2025-01-01 "
            "only."
        ),
    )
    enum_values: Optional[list[EnumValue]] = Field(
        default=None,
        description=(
            "For an enum variable, each value it can take with its label, in "
            "the order the country model declares them. possible_values holds "
            "the same names without labels. None for other variables, and for "
            "an enum that declares a value other than a string, number, "
            "boolean or None."
        ),
    )

    @field_validator("reference", mode="before")
    @classmethod
    def normalize_reference(cls, value: Any) -> Optional[list[Any]]:
        """Return references as a JSON-safe list."""

        if value is None:
            return None
        references = value if isinstance(value, (list, tuple)) else [value]
        return [_json_safe(item) for item in references]

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: Any) -> dict[str, Any]:
        """Return arbitrary country metadata as a JSON-safe mapping."""

        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError("Variable metadata must be a mapping")
        return {str(key): _json_safe(item) for key, item in value.items()}


def _json_safe(value: Any) -> Any:
    """Normalize country-model metadata without retaining runtime objects."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    return str(value)
