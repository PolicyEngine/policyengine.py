from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .model import Model
from .versioned_dataset import VersionedDataset


class Dataset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    version: str | None = None
    versioned_dataset: VersionedDataset | None = None
    year: int | None = None
    data: Any | None = None
    model: Model | None = None
