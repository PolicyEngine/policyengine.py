from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .model import Model


class ModelVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    model: Model
    version: str
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
