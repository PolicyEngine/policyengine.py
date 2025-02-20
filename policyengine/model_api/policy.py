from pydantic import BaseModel

class Policy(BaseModel):
    parameter_changes: dict