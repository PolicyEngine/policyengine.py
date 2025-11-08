from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .tax_benefit_model import TaxBenefitModel


class TaxBenefitModelVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    model: TaxBenefitModel
    version: str
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
