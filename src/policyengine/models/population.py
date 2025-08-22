"""Population model for grouping entities in a simulation run."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class Population(BaseModel):
    """Represents a population for a simulation run."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Name of the population")
    country: str = Field(..., description="Country code")
    year: int = Field(..., description="Year of the population data")
    scenario_id: Optional[str] = Field(None, description="Associated scenario ID")
    entity_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Number of entities by type"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_entity_count(self, entity_type: str, count: int) -> None:
        """Add or update entity count for a type."""
        self.entity_counts[entity_type] = count
        self.updated_at = datetime.now()
    
    def total_entities(self) -> int:
        """Get total number of entities across all types."""
        return sum(self.entity_counts.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "year": self.year,
            "scenario_id": self.scenario_id,
            "entity_counts": self.entity_counts,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def summary(self) -> str:
        """Get a summary of the population."""
        entity_summary = ", ".join(
            f"{count:,} {entity_type}s" 
            for entity_type, count in self.entity_counts.items()
        )
        return (
            f"Population '{self.name}' ({self.country}, {self.year}): "
            f"{entity_summary}"
        )