from typing import Any, Literal, Optional, Type

from pydantic import BaseModel, Field

from policyengine.utils.reforms import ParametricReform
from policyengine_core.reforms import Reform as StructuralReform


CountryType = Literal["uk", "us"]
ScopeType = Literal["household", "macro"]
DataType = (
    str | dict[Any, Any] | Any | None
)  # Needs stricter typing. Any==policyengine_core.data.Dataset, but pydantic refuses for some reason.
TimePeriodType = int
ReformType = ParametricReform | Type[StructuralReform] | None
RegionType = Optional[str]
SubsampleType = Optional[int]


class SimulationOptions(BaseModel):
    country: CountryType = Field(..., description="The country to simulate.")
    scope: ScopeType = Field(..., description="The scope of the simulation.")
    data: DataType = Field(None, description="The data to simulate.")
    time_period: TimePeriodType = Field(
        2025, description="The time period to simulate."
    )
    reform: ReformType = Field(None, description="The reform to simulate.")
    baseline: ReformType = Field(None, description="The baseline to simulate.")
    region: RegionType = Field(
        None, description="The region to simulate within the country."
    )
    subsample: SubsampleType = Field(
        None,
        description="How many, if a subsample, households to randomly simulate.",
    )
    title: Optional[str] = Field(
        "[Analysis title]",
        description="The title of the analysis (for charts). If not provided, a default title will be generated.",
    )
    include_cliffs: Optional[bool] = Field(
        False,
        description="Whether to include tax-benefit cliffs in the simulation analyses. If True, cliffs will be included.",
    )
    model_version: Optional[str] = Field(
        None,
        description="The version of the country model used in the simulation. If not provided, the current package version will be used. If provided, this package will throw an error if the package version does not match. Use this as an extra safety check.",
    )
    data_version: Optional[str] = Field(
        None,
        description="The version of the data used in the simulation. If not provided, the current data version will be used. If provided, this package will throw an error if the data version does not match. Use this as an extra safety check.",
    )

    model_config = {
        "arbitrary_types_allowed": True,
    }
