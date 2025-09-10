"""Registry system for custom report items.

This module provides a plugin system that allows users to register
custom report item types without modifying core PolicyEngine code.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from sqlmodel import SQLModel
    from .base import ReportElementDataItem


class ReportItemRegistry:
    """Central registry for report item types.
    
    This registry maintains mappings between:
    - Model classes (Pydantic models for computation)
    - Table classes (SQLModel tables for storage)
    - Mapper functions (conversion between models and tables)
    """
    
    _items: Dict[str, Dict[str, Any]] = {}
    _model_to_name: Dict[type, str] = {}
    _table_to_name: Dict[type, str] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        model_class: Type["ReportElementDataItem"],
        table_class: Type["SQLModel"],
        to_table_mapper: Optional[Callable] = None,
        from_table_mapper: Optional[Callable] = None,
    ) -> None:
        """Register a custom report item type.
        
        Args:
            name: Unique identifier for this report item type
            model_class: Pydantic model class for computation
            table_class: SQLModel table class for storage
            to_table_mapper: Function to convert model to table
                Signature: (item: model_class, session: Session, **kwargs) -> table_class
            from_table_mapper: Function to convert table to model
                Signature: (row: table_class, session: Session) -> model_class
        """
        if name in cls._items:
            raise ValueError(f"Report item type '{name}' is already registered")
        
        cls._items[name] = {
            "model": model_class,
            "table": table_class,
            "to_table": to_table_mapper,
            "from_table": from_table_mapper,
        }
        
        cls._model_to_name[model_class] = name
        cls._table_to_name[table_class] = name
    
    @classmethod
    def get_by_name(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get report item registration by name."""
        return cls._items.get(name)
    
    @classmethod
    def get_by_model(cls, model_class: type) -> Optional[Dict[str, Any]]:
        """Get report item registration by model class."""
        name = cls._model_to_name.get(model_class)
        return cls._items.get(name) if name else None
    
    @classmethod
    def get_by_table(cls, table_class: type) -> Optional[Dict[str, Any]]:
        """Get report item registration by table class."""
        name = cls._table_to_name.get(table_class)
        return cls._items.get(name) if name else None
    
    @classmethod
    def list_registered(cls) -> list[str]:
        """List all registered report item types."""
        return list(cls._items.keys())
    
    @classmethod
    def is_registered_model(cls, model_class: type) -> bool:
        """Check if a model class is registered."""
        return model_class in cls._model_to_name
    
    @classmethod
    def is_registered_table(cls, table_class: type) -> bool:
        """Check if a table class is registered."""
        return table_class in cls._table_to_name
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (useful for testing)."""
        cls._items.clear()
        cls._model_to_name.clear()
        cls._table_to_name.clear()