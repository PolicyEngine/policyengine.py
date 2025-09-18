from pydantic import BaseModel
from datetime import datetime
from .model import Model

class BaselineVariable(BaseModel):
    id: str
    model: Model
    entity: str
    label: str | None = None
    description: str | None = None
    data_type: type | None = None
    
