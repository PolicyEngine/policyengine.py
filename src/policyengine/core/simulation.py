from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .cache import LRUCache
from .dataset import Dataset
from .dynamic import Dynamic
from .policy import Policy
from .tax_benefit_model_version import TaxBenefitModelVersion

_cache: LRUCache["Simulation"] = LRUCache(max_size=100)


class Simulation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    policy: Policy | None = None
    dynamic: Dynamic | None = None
    dataset: Dataset = None

    tax_benefit_model_version: TaxBenefitModelVersion = None
    output_dataset: Dataset | None = None

    def run(self):
        self.tax_benefit_model_version.run(self)

    def ensure(self):
        cached_result = _cache.get(self.id)
        if cached_result:
            self.output_dataset = cached_result.output_dataset
            return
        try:
            self.tax_benefit_model_version.load(self)
        except Exception:
            self.run()
            self.save()

        _cache.add(self.id, self)

    def save(self):
        """Save the simulation's output dataset."""
        self.tax_benefit_model_version.save(self)

    def load(self):
        """Load the simulation's output dataset."""
        self.tax_benefit_model_version.load(self)
