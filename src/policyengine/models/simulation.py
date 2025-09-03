"""Simulation model for PolicyEngine.

Defines the `Simulation` pydantic model and its `run` entrypoint wrapper
for country-specific implementations.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .dataset import Dataset
from .dynamics import Dynamics
from .enums import OperationStatus
from .policy import Policy
from policyengine.utils.version import get_model_version


class Simulation(BaseModel):
    """Metadata for simulation. Re-implemented by country versions."""

    # Foreign key references
    dataset: Dataset
    policy: Policy
    dynamics: Dynamics
    result: Any | None = None
    model_version: str | None
    country: str

    # Processing metadata
    status: OperationStatus = OperationStatus.PENDING
    created_at: datetime = datetime.now()
    completed_at: datetime | None = None

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
        self.model_version = get_model_version(self.country)
        return self.dataset
