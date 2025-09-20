from collections.abc import Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlmodel import SQLModel, select

if TYPE_CHECKING:
    from .database import Database


class TableLink(BaseModel):
    model_cls: type[BaseModel]
    table_cls: type[SQLModel]
    model_to_table_custom_transforms: dict[str, Callable] | None = None
    table_to_model_custom_transforms: dict[str, Callable] | None = None
    primary_key: str | tuple[str, ...] = (
        "id"  # Allow multiple strings in tuple
    )

    def get(self, database: "Database", **kwargs):
        statement = select(self.table_cls).filter_by(**kwargs)
        result = database.session.exec(statement).first()
        if result is None:
            return None
        model_data = result.model_dump()
        if self.table_to_model_custom_transforms:
            for (
                field,
                transform,
            ) in self.table_to_model_custom_transforms.items():
                model_data[field] = transform(getattr(result, field))

        # Only include fields that exist in the model class
        valid_fields = {
            field_name for field_name in self.model_cls.__annotations__.keys()
        }
        filtered_model_data = {
            k: v for k, v in model_data.items() if k in valid_fields
        }
        return self.model_cls(**filtered_model_data)

    def set(self, database: "Database", obj: BaseModel, commit: bool = True):
        model_data = obj.model_dump()
        if self.model_to_table_custom_transforms:
            for (
                field,
                transform,
            ) in self.model_to_table_custom_transforms.items():
                model_data[field] = transform(obj)
        # Only include fields that exist in the table class
        valid_fields = {
            field_name for field_name in self.table_cls.__annotations__.keys()
        }
        filtered_model_data = {
            k: v for k, v in model_data.items() if k in valid_fields
        }
        table_obj = self.table_cls(**filtered_model_data)

        # Check if already exists using primary key
        query = select(self.table_cls)
        if isinstance(self.primary_key, tuple):
            for key in self.primary_key:
                query = query.where(
                    getattr(self.table_cls, key) == getattr(table_obj, key)
                )
        else:
            query = query.where(
                getattr(self.table_cls, self.primary_key)
                == getattr(table_obj, self.primary_key)
            )

        existing = database.session.exec(query).first()
        if existing:
            # Update existing record
            for key, value in filtered_model_data.items():
                setattr(existing, key, value)
            database.session.add(existing)
        else:
            database.session.add(table_obj)

        if commit:
            database.session.commit()
