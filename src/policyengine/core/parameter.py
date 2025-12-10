from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, Field, PrivateAttr

from .parameter_value import ParameterValue
from .tax_benefit_model_version import TaxBenefitModelVersion

if TYPE_CHECKING:
    from .parameter_value import ParameterValue


class Parameter(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    label: str | None = None
    description: str | None = None
    data_type: type | None = None
    tax_benefit_model_version: TaxBenefitModelVersion
    unit: str | None = None

    # Lazy loading: store core param ref, build values on demand
    _core_param: Any = PrivateAttr(default=None)
    _parameter_values: list["ParameterValue"] | None = PrivateAttr(
        default=None
    )

    def __init__(self, _core_param: Any = None, **data):
        super().__init__(**data)
        self._core_param = _core_param
        self._parameter_values = None

    @property
    def parameter_values(self) -> list["ParameterValue"]:
        """Lazily build parameter values on first access."""
        if self._parameter_values is None:
            self._parameter_values = []
            if self._core_param is not None:
                from policyengine.utils import parse_safe_date

                for i in range(len(self._core_param.values_list)):
                    param_at_instant = self._core_param.values_list[i]
                    if i + 1 < len(self._core_param.values_list):
                        next_instant = self._core_param.values_list[i + 1]
                    else:
                        next_instant = None
                    pv = ParameterValue(
                        parameter=self,
                        start_date=parse_safe_date(
                            param_at_instant.instant_str
                        ),
                        end_date=parse_safe_date(next_instant.instant_str)
                        if next_instant
                        else None,
                        value=param_at_instant.value,
                    )
                    self._parameter_values.append(pv)
        return self._parameter_values

    @parameter_values.setter
    def parameter_values(self, value: list["ParameterValue"]) -> None:
        """Allow direct setting of parameter values."""
        self._parameter_values = value
