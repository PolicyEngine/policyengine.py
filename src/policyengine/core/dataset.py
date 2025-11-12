from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .tax_benefit_model import TaxBenefitModel
from .dataset_version import DatasetVersion



class Dataset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    dataset_version: DatasetVersion | None = None
    filepath: str
    is_output_dataset: bool = False
    tax_benefit_model: TaxBenefitModel = None
