"""Variable model for PolicyEngine.

Represents a model variable and associated metadata.
"""

from pydantic import BaseModel


class Variable(BaseModel):
    """PolicyEngine variable concept- an attribute of an entity."""

    name: str

    # Variable metadata
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    value_type: str  # "float", "int", "bool", "string", "enum"
    entity: str  # "person", "household", "tax_unit", etc.
    definition_period: str | None = None  # "year", "month", "eternity"
    country: str | None = None
