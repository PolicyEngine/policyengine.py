from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlmodel import Field, SQLModel
from pydantic import BaseModel

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class UserDynamicTable(SQLModel, table=True):
    __tablename__ = "user_dynamics"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    dynamic_id: str = Field(foreign_key="dynamics.id", nullable=False)
    custom_name: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# Create a dummy model class for the table link
class UserDynamic(BaseModel):
    pass


user_dynamic_table_link = TableLink(
    model_cls=UserDynamic,
    table_cls=UserDynamicTable,
)