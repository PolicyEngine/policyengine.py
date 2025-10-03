import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel
from typing import TYPE_CHECKING

from policyengine.models.user import User

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class UserTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "users"

    id: str = Field(
        primary_key=True, default_factory=lambda: str(uuid.uuid4())
    )
    username: str = Field(nullable=False, unique=True)
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    email: str | None = Field(default=None)
    current_model_id: str = Field(default="policyengine_uk")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def convert_from_model(cls, model: User, database: "Database" = None) -> "UserTable":
        """Convert a User instance to a UserTable instance."""
        return cls(
            id=model.id,
            username=model.username,
            first_name=model.first_name,
            last_name=model.last_name,
            email=model.email,
            current_model_id=model.current_model_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def convert_to_model(self, database: "Database" = None) -> User:
        """Convert this UserTable instance to a User instance."""
        return User(
            id=self.id,
            username=self.username,
            first_name=self.first_name,
            last_name=self.last_name,
            email=self.email,
            current_model_id=self.current_model_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


user_table_link = TableLink(
    model_cls=User,
    table_cls=UserTable,
)
