from pydantic import BaseModel

class Dataset(BaseModel):
    data: str | None = None
    situation: dict | None = None