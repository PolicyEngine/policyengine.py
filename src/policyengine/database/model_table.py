from sqlmodel import SQLModel, Field
from policyengine.models import Model
from typing import Optional
from .link import TableLink
from policyengine.utils.compress import compress_data, decompress_data


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
        simulation_function=lambda m: compress_data(m.simulation_function),
    ),
    table_to_model_custom_transforms=dict(
        simulation_function=lambda b: decompress_data(b),
    ),
)
