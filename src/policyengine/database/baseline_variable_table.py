from sqlmodel import Field, SQLModel

from policyengine.models import BaselineVariable
from policyengine.utils.compress import compress_data, decompress_data

from .link import TableLink


class BaselineVariableTable(SQLModel, table=True):
    __tablename__ = "baseline_variables"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(primary_key=True)  # Variable name
    model_id: str = Field(
        primary_key=True, foreign_key="models.id"
    )  # Part of composite key
    model_version_id: str = Field(
        foreign_key="model_versions.id", ondelete="CASCADE"
    )
    entity: str = Field(nullable=False)
    label: str | None = Field(default=None)
    description: str | None = Field(default=None)
    data_type: bytes | None = Field(default=None)  # Pickled type


baseline_variable_table_link = TableLink(
    model_cls=BaselineVariable,
    table_cls=BaselineVariableTable,
    primary_key=("id", "model_id"),  # Composite primary key
    model_to_table_custom_transforms=dict(
        model_id=lambda bv: bv.model_version.model.id,  # Add model_id from model_version
        model_version_id=lambda bv: bv.model_version.id,
        data_type=lambda bv: compress_data(bv.data_type)
        if bv.data_type
        else None,
    ),
    table_to_model_custom_transforms=dict(
        data_type=lambda dt: decompress_data(dt) if dt else None,
    ),
)
