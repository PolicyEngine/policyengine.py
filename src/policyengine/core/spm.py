"""Dependency-light public models for US SPM selection and calculation receipts."""

from datetime import date
from typing import Any, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)


def _selection_schema(schema: dict[str, Any]) -> None:
    """Keep generated clients from replacing inherited settings with defaults."""
    for field in schema.get("properties", {}).values():
        field.pop("default", None)


class SPMSelection(BaseModel):
    """Select from the bundle's pinned artifact; national geography is explicit.

    County mode reads the household's observed ``county_fips``. A state alone
    does not identify an SPM area. These settings contain no provider or path.
    Serialization preserves omitted options so they still inherit bundle defaults
    after a round trip. A resolved selection explicitly contains all six fields.
    """

    model_config = ConfigDict(
        frozen=True, extra="forbid", json_schema_extra=_selection_schema
    )

    forecast_content_sha256: Optional[str] = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    scenario: Optional[str] = Field(default=None, min_length=1, pattern=r"^\S+$")
    geography_kind: Literal["county", "national", "metro"] = "county"
    geography_id: Optional[str] = Field(default=None, min_length=1)
    county_vintage: str = Field(default="2020", pattern=r"^[0-9]{4}$")
    as_of: Optional[str] = None

    @model_serializer(mode="wrap")
    def serialize_selection(self, handler: SerializerFunctionWrapHandler):
        """Keep inherited defaults distinct from explicit options in nested JSON."""
        return {
            name: value
            for name, value in handler(self).items()
            if name in self.model_fields_set
        }

    @field_validator("as_of")
    @classmethod
    def validate_as_of(cls, value):
        if value is not None:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError("as_of must be an ISO calendar date (YYYY-MM-DD)")
        return value

    @model_validator(mode="after")
    def validate_location(self):
        if self.geography_kind == "metro":
            if not self.geography_id or not self.geography_id.strip():
                raise ValueError("An SPM area selection requires geography_id")
        elif self.geography_id is not None:
            raise ValueError("Only an SPM area selection accepts geography_id")
        return self


class SPMProvenance(BaseModel):
    """Detached calculation receipt; data certification is a separate claim."""

    model_config = ConfigDict(extra="forbid")

    forecast_id: str
    forecast_sha256: str
    scenario: str
    geography_kind: str
    runtime_versions: dict[str, Optional[str]]
    years: dict[str, dict[str, Any]]
    geographies: list[dict[str, Any]]
    composition_method: str
    storage_method: str
