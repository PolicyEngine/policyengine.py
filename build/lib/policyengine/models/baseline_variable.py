from pydantic import BaseModel

from .model_version import ModelVersion


class BaselineVariable(BaseModel):
    id: str
    model_version: ModelVersion
    entity: str
    label: str | None = None
    description: str | None = None
    data_type: type | None = None
