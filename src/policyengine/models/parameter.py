from uuid import uuid4

from pydantic import BaseModel, Field

from .model import Model


class Parameter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    description: str | None = None
    data_type: type | None = None
    model: Model | None = None
