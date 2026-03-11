from typing import Any

from pydantic import BaseModel

from .tax_benefit_model_version import TaxBenefitModelVersion


class Variable(BaseModel):
    id: str
    name: str
    label: str | None = None
    tax_benefit_model_version: TaxBenefitModelVersion
    entity: str
    description: str | None = None
    data_type: type = None
    possible_values: list[Any] | None = None
    default_value: Any = None
    value_type: type | None = None
    adds: list[str] | None = None
    subtracts: list[str] | None = None
