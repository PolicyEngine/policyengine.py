from pydantic import BaseModel
from uuid import uuid4
from .model import Model


class VersionedDataset(BaseModel):
    id: str = str(uuid4())
    name: str
    description: str
    model: Model | None = None
