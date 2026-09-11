"""Typed operator input for SPM bundle configuration."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from policyengine.provenance.bundle_validation import validate_spm_configuration


class SPMMeasurementConfiguration(BaseModel):
    """Canonical SPM defaults; this pin is not a data certification claim."""

    model_config = ConfigDict(extra="forbid", strict=True)

    forecast_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario: str = Field(min_length=1, pattern=r"^\S+$")
    geography_kind: Literal["county", "metro", "national"] = "county"
    geography_id: Optional[str] = None
    county_vintage: str = Field(default="2020", pattern=r"^[0-9]{4}$")
    as_of: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def canonical_defaults(cls, value):
        validate_spm_configuration(value)
        return value
