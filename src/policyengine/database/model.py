from sqlmodel import SQLModel, Field, select
import pickle
from policyengine.models import Model, ModelVersion
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import uuid4

if TYPE_CHECKING:
    from .database import Database

from .link import TableLink


class ModelTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "models"
    
    id: str = Field(primary_key=True)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    simulation_function: bytes
    

model_table_link = TableLink(
    model_cls=Model,
    table_cls=ModelTable,
    model_to_table_custom_transforms=dict(
        simulation_function=pickle.dumps,
    ),
    table_to_model_custom_transforms=dict(
        simulation_function=pickle.loads,
    ),
)

class ModelVersionTable(SQLModel, table=True):
    __tablename__ = "model_versions"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    model_id: str = Field(foreign_key="models.id", ondelete="CASCADE")
    version: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)

model_version_table_link = TableLink(
    model_cls=ModelVersion,
    table_cls=ModelVersionTable,
    model_to_table_custom_transforms=dict(
        model_id=lambda model_version: model_version.model.id,
    ),
    table_to_model_custom_transforms={}
)