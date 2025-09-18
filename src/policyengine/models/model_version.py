from pydantic import BaseModel
from datetime import datetime
from .model import Model
from uuid import uuid4


class ModelVersion(BaseModel):
    id: str = str(uuid4())
    model: Model
    version: str
    description: str | None = None
    created_at: datetime = datetime.now()
