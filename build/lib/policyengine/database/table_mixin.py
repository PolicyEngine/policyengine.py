from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from pydantic import BaseModel
from sqlmodel import SQLModel

if TYPE_CHECKING:
    from .database import Database

T = TypeVar("T", bound=BaseModel)


class TableConversionMixin:
    """Mixin class for SQLModel tables to provide conversion methods between table instances and Pydantic models."""

    _model_cls: ClassVar[type[BaseModel]] = None
    _foreign_key_fields: ClassVar[dict[str, type[BaseModel]]] = {}

    @classmethod
    def convert_from_model(cls, model: BaseModel, database: "Database" = None) -> SQLModel:
        """Convert a Pydantic model instance to a table instance, resolving foreign objects to IDs.

        Args:
            model: The Pydantic model instance to convert
            database: The database instance for resolving foreign objects (optional)

        Returns:
            An instance of the SQLModel table class
        """
        data = {}

        for field_name in cls.__annotations__.keys():
            # Check if this field is a foreign key that needs resolution
            if field_name in cls._foreign_key_fields:
                # Extract ID from the nested object
                nested_obj = getattr(model, field_name.replace("_id", ""), None)
                if nested_obj:
                    # If we need to ensure the foreign object exists in DB
                    if database:
                        database.set(nested_obj, commit=False)
                    data[field_name] = nested_obj.id if hasattr(nested_obj, "id") else None
                else:
                    data[field_name] = None
            elif hasattr(model, field_name):
                # Direct field mapping
                data[field_name] = getattr(model, field_name)

        return cls(**data)

    @classmethod
    def convert_to_model(cls, table_instance: SQLModel, database: "Database" = None) -> BaseModel:
        """Convert a table instance to a Pydantic model, resolving foreign key IDs to objects.

        Args:
            table_instance: The SQLModel table instance to convert
            database: The database instance for resolving foreign keys (required if foreign keys exist)

        Returns:
            An instance of the Pydantic model class
        """
        if cls._model_cls is None:
            raise ValueError(f"Model class not set for {cls.__name__}")

        data = {}

        for field_name in cls._model_cls.__annotations__.keys():
            # Check if we need to resolve a foreign key
            fk_field = f"{field_name}_id"
            if fk_field in cls._foreign_key_fields and database:
                # Resolve the foreign key to an object
                fk_id = getattr(table_instance, fk_field, None)
                if fk_id:
                    foreign_model_cls = cls._foreign_key_fields[fk_field]
                    data[field_name] = database.get(foreign_model_cls, id=fk_id)
                else:
                    data[field_name] = None
            elif hasattr(table_instance, field_name):
                # Direct field mapping
                data[field_name] = getattr(table_instance, field_name)

        return cls._model_cls(**data)