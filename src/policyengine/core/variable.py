from typing import Any, Optional

from pydantic import BaseModel

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
