from pydantic import BaseModel
from sqlmodel import SQLModel


class TableLink(BaseModel):
    """Simple registry mapping model classes to table classes."""
    model_cls: type[BaseModel]
    table_cls: type[SQLModel]
