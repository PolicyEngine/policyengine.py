from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

from .tax_benefit_model import TaxBenefitModel

if TYPE_CHECKING:
    from .dataset import Dataset


class DatasetVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    dataset: "Dataset"
    description: str
    tax_benefit_model: TaxBenefitModel = None
