import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from policyengine.models.user import User

from .link import TableLink


class UserTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "users"

    id: str = Field(
        primary_key=True, default_factory=lambda: str(uuid.uuid4())
    )
    username: str = Field(nullable=False, unique=True)
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    email: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


user_table_link = TableLink(
    model_cls=User,
    table_cls=UserTable,
)
