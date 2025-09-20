from uuid import uuid4

from pydantic import BaseModel, Field

from .model import Model


class VersionedDataset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    model: Model | None = None
