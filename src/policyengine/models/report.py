from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    created_at: Optional[datetime] = None
