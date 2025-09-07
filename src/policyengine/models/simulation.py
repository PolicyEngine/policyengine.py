"""Simulation model for PolicyEngine.

Defines the `Simulation` pydantic model and its `run` entrypoint wrapper
for country-specific implementations.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator, model_validator
from uuid import UUID

from .dataset import Dataset
from .dynamic import Dynamic
from .enums import OperationStatus, DatasetType
from .policy import Policy
from policyengine.utils.version import get_model_version


class Simulation(BaseModel):
    """Metadata for simulation. Re-implemented by country versions."""

    id: UUID | None = None
    # Foreign key references
    dataset: Dataset
    policy: Policy
    dynamic: Dynamic
    result: Any | None = None
    model_version: str | None = None
    country: str | None = None

    # Processing metadata
    status: OperationStatus = OperationStatus.PENDING
    created_at: datetime = datetime.now()
    completed_at: datetime | None = None
    
    @model_validator(mode='after')
    def infer_country_and_version(self):
        """Infer country from dataset type and model_version from country package."""
        # Infer country from dataset if not provided
        if self.country is None and self.dataset and hasattr(self.dataset, 'dataset_type'):
            if self.dataset.dataset_type == DatasetType.UK:
                self.country = 'uk'
            elif self.dataset.dataset_type == DatasetType.US:
                self.country = 'us'
        
        # Infer model_version from country package if not provided
        if self.model_version is None and self.country:
            self.model_version = get_model_version(self.country)
            
        return self

    def run(self) -> Dataset:
        """Run the simulation."""
        if self.country == "uk":
            from policyengine.countries.uk.simulation import run_uk_simulation

            run_uk_simulation(self)
        elif self.country == "us":
            from policyengine.countries.us.simulation import run_us_simulation

            run_us_simulation(self)

        self.status = OperationStatus.COMPLETED
        self.completed_at = datetime.now()
        # Model version already set by validator, but update if not set
        if self.model_version is None:
            self.model_version = get_model_version(self.country)
        return self.dataset
