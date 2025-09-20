import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    created_at: datetime | None = None
