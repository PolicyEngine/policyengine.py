from pydantic import BaseModel, Field
from datetime import datetime
from .model import Model
from uuid import uuid4


class ModelVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    model: Model
    version: str
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
