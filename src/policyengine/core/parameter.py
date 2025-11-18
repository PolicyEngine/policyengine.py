from uuid import uuid4

from pydantic import BaseModel, Field

from .tax_benefit_model_version import TaxBenefitModelVersion


class Parameter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    label: str | None = None
    description: str | None = None
    data_type: type | None = None
    tax_benefit_model_version: TaxBenefitModelVersion
    unit: str | None = None
