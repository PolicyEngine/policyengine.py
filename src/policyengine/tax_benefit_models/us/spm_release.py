"""Typed, serializable selection of an optional SPM release provider."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SPMReleaseSelection(BaseModel):
    """Pin local release bytes or explicitly select the package's bundled release.

    An external file requires its independently retained expected hash. This
    object holds no executable callback and does not certify population data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    path: Optional[str] = None
    expected_sha256: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    release_id: Optional[str] = None
    year_policy: Literal["error", "pe_cpi_u"] = "pe_cpi_u"
    allow_estimated: bool = False
    geography_kind: Literal[
        "national", "metro", "congressional_district", "explicit"
    ] = "national"
    geography_id: Optional[str] = None
    geographic_adjustment: Optional[float] = Field(
        default=None, gt=0, allow_inf_nan=False
    )
    geography_vintage: Optional[str] = None
    missing_geography: Literal["error", "national"] = "error"
    as_of: Optional[str] = None

    @model_validator(mode="after")
    def require_external_digest(self):
        if self.path is not None and self.expected_sha256 is None:
            raise ValueError("An explicit release path requires expected_sha256")
        return self

    def create_provider(self):
        from spm_calculator.policyengine_adapter import PolicyEngineSPMProvider
        from spm_calculator.release import load_release

        release = load_release(
            self.path, expected_sha256=self.expected_sha256, as_of=self.as_of
        )
        if self.release_id is not None and self.release_id != release.release_id:
            raise ValueError("Loaded SPM release does not match release_id")
        options = self.model_dump(exclude={"path", "expected_sha256", "release_id"})
        return PolicyEngineSPMProvider(release, **options)


class SPMIntegrationProvenance(BaseModel):
    """JSON-safe receipt of what the SPM formulas actually evaluated."""

    integration_status: Literal["development_household_integration"]
    release_id: str
    release_sha256: str
    information_date: str
    year_policy: str
    allow_estimated: bool
    missing_geography: str
    runtime_versions: dict[str, Optional[str]]
    years: dict[str, dict[str, Any]]
    geographies: list[dict[str, Any]]
    composition_method: str
    population_data_certified: Literal[False]
