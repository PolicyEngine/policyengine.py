"""Lazy loading utilities for entity schemas."""

from typing import Type, Optional, Dict, Any
from ..models.base import BaseEntity


class LazyEntityProxy:
    """Proxy class that loads the actual entity class on first access."""
    
    def __init__(self, loader_func, schema_key: str):
        self._loader_func = loader_func
        self._schema_key = schema_key
        self._cached_class: Optional[Type[BaseEntity]] = None
    
    def _load(self):
        """Load the actual class if not already loaded."""
        if self._cached_class is None:
            schemas = self._loader_func()
            self._cached_class = schemas[self._schema_key]
        return self._cached_class
    
    def __call__(self, *args, **kwargs):
        """Allow instantiation like a normal class."""
        actual_class = self._load()
        return actual_class(*args, **kwargs)
    
    def __getattr__(self, name):
        """Forward attribute access to the actual class."""
        actual_class = self._load()
        return getattr(actual_class, name)
    
    def __instancecheck__(self, instance):
        """Support isinstance checks."""
        actual_class = self._load()
        return isinstance(instance, actual_class)
    
    def __subclasscheck__(self, subclass):
        """Support issubclass checks."""
        actual_class = self._load()
        return issubclass(subclass, actual_class)