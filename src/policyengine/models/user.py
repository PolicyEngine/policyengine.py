import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    current_model_id: str = "policyengine_uk"  # Default to UK model
    created_at: datetime | None = None
    updated_at: datetime | None = None
