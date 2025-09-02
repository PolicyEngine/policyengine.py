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


class Simulation(BaseModel):
    """Metadata for simulation. Re-implemented by country versions."""

    # Foreign key references
    dataset: Dataset
    policy: Policy
    dynamics: Dynamics
    output_data: Any | None = None
    model_version: str | None = None
    country: str

    # Processing metadata
    status: OperationStatus = OperationStatus.PENDING
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    def run(self) -> Dataset:
        """Run the simulation."""
        if self.country == "uk":
            from policyengine.countries.uk.simulation import run_uk_simulation

            return run_uk_simulation(self)
