"""Data-only configuration for adapter-local behavior inputs."""

from typing import Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator

from .dataset import YearData

__all__ = ["BehaviorInputBinding", "BehaviorInputs"]


class BehaviorInputBinding(BaseModel):
    """Bind an adapter-local role to one population entity column."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    entity: str
    column: str


class BehaviorInputs(BaseModel):
    """Immutable population-column bindings for a behavior adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bindings: tuple[BehaviorInputBinding, ...]

    @field_validator("bindings")
    @classmethod
    def _roles_must_be_unique(
        cls,
        bindings: tuple[BehaviorInputBinding, ...],
    ) -> tuple[BehaviorInputBinding, ...]:
        seen: set[str] = set()
        duplicates: list[str] = []
        for binding in bindings:
            if binding.role in seen and binding.role not in duplicates:
                duplicates.append(binding.role)
            seen.add(binding.role)
        if duplicates:
            raise ValueError(
                "Behavior input roles contain duplicate adapter-local labels: "
                f"{duplicates}."
            )
        return bindings


def _resolve_behavior_inputs(
    behavior_inputs: BehaviorInputs,
    data: Optional[YearData],
) -> dict[str, pd.Series]:
    """Resolve bindings to copied values indexed only by their entity IDs."""
    if data is None:
        raise ValueError("Behavior input resolution requires loaded YearData.")

    entity_data = data.entity_data
    if entity_data is None:
        raise ValueError("Behavior input resolution requires loaded YearData.")

    resolved: dict[str, pd.Series] = {}
    for binding in behavior_inputs.bindings:
        if binding.entity not in entity_data:
            raise ValueError(
                f"Behavior input role {binding.role!r} references missing entity "
                f"{binding.entity!r}."
            )

        entity_table = entity_data[binding.entity]
        if entity_table is None:
            raise ValueError(
                f"Behavior input role {binding.role!r} references entity "
                f"{binding.entity!r} without loaded data."
            )
        table = pd.DataFrame(entity_table)
        id_column = f"{binding.entity}_id"
        if id_column not in table.columns:
            raise ValueError(
                f"Behavior input entity {binding.entity!r} is missing required ID "
                f"column {id_column!r}."
            )

        ids = table[id_column].copy(deep=True)
        if ids.isna().any():
            raise ValueError(
                f"Behavior input entity {binding.entity!r} has null values in "
                f"required ID column {id_column!r}."
            )
        duplicate_ids = ids.duplicated(keep=False)
        if duplicate_ids.any():
            duplicate_values = ids.loc[duplicate_ids].drop_duplicates().tolist()
            raise ValueError(
                f"Behavior input entity {binding.entity!r} must have unique "
                f"{id_column!r} values; duplicates: {duplicate_values}."
            )

        if binding.column not in table.columns:
            raise ValueError(
                f"Behavior input role {binding.role!r} references missing column "
                f"{binding.column!r} on entity {binding.entity!r}."
            )

        values = table[binding.column].copy(deep=True)
        values.index = pd.Index(ids.array.copy(), name=id_column)
        resolved[binding.role] = values

    return resolved
