from sqlmodel import SQLModel, Field
from policyengine.models.user import User
from typing import Optional
from datetime import datetime
from .link import TableLink
import uuid


class UserTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "users"

    id: str = Field(
        primary_key=True, default_factory=lambda: str(uuid.uuid4())
    )
    username: str = Field(nullable=False, unique=True)
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


user_table_link = TableLink(
    model_cls=User,
    table_cls=UserTable,
)
