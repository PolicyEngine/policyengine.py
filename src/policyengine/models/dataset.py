from pydantic import BaseModel
from typing import Any
from uuid import uuid4
from .model import Model

class VersionedDataset(BaseModel):
    id: str = str(uuid4())
    name: str
    description: str
    model: Model | None = None

class Dataset(BaseModel):
    id: str = str(uuid4())
    name: str
    description: str
    version: str | None = None
    versioned_dataset: VersionedDataset | None = None
    year: int | None = None
    data: Any | None = None
    model: Model | None = None