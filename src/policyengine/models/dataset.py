"""Dataset model for PolicyEngine.

Defines the `Dataset` pydantic model and its basic fields.
"""

from typing import Any, Optional

from pydantic import BaseModel

from .enums import DatasetType


class Dataset(BaseModel):
    """A dataset used or created by a simulation."""

    name: str | None = None
    # Dataset characteristics
    source_dataset: Optional["Dataset"] = None
    version: str | None = None
    data: Any | None = None
    dataset_type: DatasetType
