import datetime
from collections.abc import Mapping
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator

from .tax_benefit_model_version import TaxBenefitModelVersion


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
