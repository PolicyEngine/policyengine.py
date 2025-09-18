from pydantic import BaseModel
from uuid import uuid4
from .model import Model


class Parameter(BaseModel):
    id: str = str(uuid4())
    description: str | None
    data_type: type | None
    model: Model | None = None
