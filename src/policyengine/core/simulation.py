from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from pydantic import BaseModel, Field

from .dataset import Dataset
from .dynamic import Dynamic
from .tax_benefit_model import TaxBenefitModel
from .tax_benefit_model_version import TaxBenefitModelVersion
from .policy import Policy


class Simulation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    policy: Policy | None = None
    dynamic: Dynamic | None = None
    dataset: Dataset = None

    tax_benefit_model_version: TaxBenefitModelVersion = None
    output_dataset: Dataset | None = None

    variables: Dict[str, List[str]] | None = Field(
        default=None,
        description="Optional dictionary mapping entity names to lists of variable names to calculate. If None, uses model defaults.",
    )

    def run(self):
        self.tax_benefit_model_version.run(self)
