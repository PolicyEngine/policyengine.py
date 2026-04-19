import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from .cache import LRUCache
from .dataset import Dataset
from .dynamic import Dynamic
from .policy import Policy
from .scoping_strategy import ScopingStrategy
from .tax_benefit_model_version import TaxBenefitModelVersion

logger = logging.getLogger(__name__)

_cache: LRUCache["Simulation"] = LRUCache(max_size=100)


class Simulation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    policy: Optional[Policy] = None
    dynamic: Optional[Dynamic] = None
    dataset: Dataset = None

    scoping_strategy: Optional[ScopingStrategy] = Field(
        default=None,
        description="Strategy for scoping dataset to a sub-national region",
    )

    extra_variables: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Additional variables to calculate beyond the model version's "
            "default entity_variables, keyed by entity name. Use when a "
            "caller needs variables that are not in the bundled default set."
        ),
    )

    tax_benefit_model_version: TaxBenefitModelVersion = None

    output_dataset: Optional[Dataset] = None

    def run(self):
        self.tax_benefit_model_version.run(self)

    def ensure(self):
        cached_result = _cache.get(self.id)
        if cached_result:
            self.output_dataset = cached_result.output_dataset
            return
        try:
            self.tax_benefit_model_version.load(self)
        except FileNotFoundError:
            self.run()
            self.save()
        except Exception:
            logger.warning(
                "Unexpected error loading simulation %s; falling back to run()",
                self.id,
                exc_info=True,
            )
            self.run()
            self.save()

        _cache.add(self.id, self)

    def save(self):
        """Save the simulation's output dataset."""
        self.tax_benefit_model_version.save(self)

    def load(self):
        """Load the simulation's output dataset."""
        self.tax_benefit_model_version.load(self)

    @property
    def release_bundle(self) -> dict[str, Optional[str]]:
        bundle = (
            self.tax_benefit_model_version.release_bundle
            if self.tax_benefit_model_version is not None
            else {}
        )
        return {
            **bundle,
            "dataset_filepath": self.dataset.filepath
            if self.dataset is not None
            else None,
        }
