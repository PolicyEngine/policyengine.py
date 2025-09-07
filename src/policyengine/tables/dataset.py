from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import LargeBinary, UniqueConstraint, Index
from sqlmodel import SQLModel, Field

from policyengine.models.enums import DatasetType


class DatasetTable(SQLModel, table=True):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("name", name="uq_datasets_name"),
        Index("ix_datasets_name", "name"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str | None = None
    source_dataset_id: UUID | None = Field(
        default=None, foreign_key="datasets.id"
    )
    version: str | None = None
    # Serialized bytes for SingleYearDataset (or other binary payload)
    data_bytes: bytes | None = Field(default=None, sa_type=LargeBinary)
    dataset_type: DatasetType
