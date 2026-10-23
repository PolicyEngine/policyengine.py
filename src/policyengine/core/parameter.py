from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional
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
    label: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[type] = None
    tax_benefit_model_version: TaxBenefitModelVersion
    unit: Optional[str] = None

    # Lazy loading: store core param ref, build values on demand
    _core_param: Any = PrivateAttr(default=None)
    _parameter_values: Optional[list["ParameterValue"]] = PrivateAttr(default=None)

    def __init__(self, _core_param: Any = None, **data):
        super().__init__(**data)
        self._core_param = _core_param
        self._parameter_values = None

    @property
    def parameter_values(self) -> list["ParameterValue"]:
        """Lazily build the effective parameter history on first access.

        Values are ordered from oldest to newest. ``end_date`` is inclusive,
        so each bounded value ends one day before the next value starts and the
        newest value remains open-ended. When Core exposes duplicate effective
        starts, retain the first entry because Core's lookup uses the first
        matching entry as the effective value.
        """
        if self._parameter_values is None:
            self._parameter_values = []
            if self._core_param is not None:
                from policyengine.utils import parse_safe_date

                effective_values: dict[datetime, Any] = {}
                for value_at_instant in self._core_param.values_list:
                    start_date = parse_safe_date(value_at_instant.instant_str)
                    effective_values.setdefault(start_date, value_at_instant)

                chronological_values = sorted(effective_values.items())
                for index, (start_date, value_at_instant) in enumerate(
                    chronological_values
                ):
                    next_index = index + 1
                    end_date = (
                        chronological_values[next_index][0] - timedelta(days=1)
                        if next_index < len(chronological_values)
                        else None
                    )
                    pv = ParameterValue(
                        parameter=self,
                        start_date=start_date,
                        end_date=end_date,
                        value=value_at_instant.value,
                    )
                    self._parameter_values.append(pv)
        return self._parameter_values

    @parameter_values.setter
    def parameter_values(self, value: list["ParameterValue"]) -> None:
        """Allow direct setting of parameter values."""
        self._parameter_values = value
