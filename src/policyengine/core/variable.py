from typing import Any

from pydantic import BaseModel

from .tax_benefit_model_version import TaxBenefitModelVersion


class Variable(BaseModel):
    id: str
    name: str
    tax_benefit_model_version: TaxBenefitModelVersion
    entity: str
    description: str | None = None
    data_type: type = None
    possible_values: list[Any] | None = None
