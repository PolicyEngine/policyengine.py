from .reforms import ParametricReform
from policyengine_core.reforms import Reform as StructuralReform
from typing import Type, Literal, Any

CountryType = Literal["uk", "us"]
ScopeType = Literal["household", "macro"]
DataType = (
    str | dict | Any | None
)  # Needs stricter typing. Any==policyengine_core.data.Dataset, but pydantic refuses for some reason.
TimePeriodType = int
PolicyType = (
    ParametricReform | Type[StructuralReform] | None
)
RegionType = str | None
SubsampleType = int | None