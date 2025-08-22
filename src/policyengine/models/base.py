"""Base models for PolicyEngine entities and datasets."""

from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field, ConfigDict
import pandas as pd
from datetime import datetime


class BaseEntity(BaseModel):
    """Base model for all entity types (Person, Household, etc.)."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(..., description="Unique identifier for the entity")
    weight: float = Field(1.0, description="Survey weight for the entity")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEntity":
        """Create entity from dictionary."""
        return cls(**data)


class EntityTable(BaseModel):
    """Container for a collection of entities of the same type."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    entity_type: Type[BaseEntity]
    entities: List[BaseEntity] = Field(default_factory=list)
    
    def add_entity(self, entity: BaseEntity) -> None:
        """Add an entity to the table."""
        if not isinstance(entity, self.entity_type):
            raise ValueError(f"Entity must be of type {self.entity_type.__name__}")
        self.entities.append(entity)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert entity table to pandas DataFrame."""
        return pd.DataFrame([e.to_dict() for e in self.entities])
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, entity_type: Type[BaseEntity]) -> "EntityTable":
        """Create entity table from pandas DataFrame."""
        entities = [entity_type(**row) for _, row in df.iterrows()]
        return cls(entity_type=entity_type, entities=entities)
    
    def filter(self, **kwargs) -> List[BaseEntity]:
        """Filter entities based on attributes."""
        filtered = []
        for entity in self.entities:
            match = True
            for key, value in kwargs.items():
                if not hasattr(entity, key) or getattr(entity, key) != value:
                    match = False
                    break
            if match:
                filtered.append(entity)
        return filtered
    
    def __len__(self) -> int:
        """Return number of entities in the table."""
        return len(self.entities)
    
    def __iter__(self):
        """Iterate over entities."""
        return iter(self.entities)


class SingleYearDataset(BaseModel):
    """Container for all entity tables for a single year."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    year: int = Field(..., description="Year of the dataset")
    country: str = Field(..., description="Country code (e.g., 'uk', 'us')")
    entity_tables: Dict[str, EntityTable] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    def add_table(self, name: str, table: EntityTable) -> None:
        """Add an entity table to the dataset."""
        self.entity_tables[name] = table
    
    def get_table(self, name: str) -> Optional[EntityTable]:
        """Get an entity table by name."""
        return self.entity_tables.get(name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset to dictionary format."""
        return {
            "year": self.year,
            "country": self.country,
            "entity_tables": {
                name: table.to_dataframe().to_dict(orient="records")
                for name, table in self.entity_tables.items()
            },
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get summary statistics for the dataset."""
        return {
            "year": self.year,
            "country": self.country,
            "tables": {
                name: {
                    "count": len(table),
                    "entity_type": table.entity_type.__name__
                }
                for name, table in self.entity_tables.items()
            },
            "created_at": self.created_at.isoformat()
        }