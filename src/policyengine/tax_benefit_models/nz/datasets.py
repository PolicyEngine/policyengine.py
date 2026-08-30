"""Read-only NZ pilot datasets with Frame-owned household weight inheritance.

The public transport artifact contains person, household, and family tables.
Only household weights are stored. Effective person/family weights are resolved
by Microcosm and exposed as in-memory MicroDataFrame weights for PolicyEngine.
"""

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, Optional

import numpy as np
import pandas as pd
from microdf import MicroDataFrame
from pydantic import Field

from policyengine.core import Dataset, YearData

ENTITIES = ("person", "household", "family")


class NZYearData(YearData):
    """Entity-level NZ pilot data; effective weights exist only in memory."""

    person: MicroDataFrame
    household: MicroDataFrame
    family: MicroDataFrame

    @property
    def entity_data(self) -> dict[str, MicroDataFrame]:
        return {entity: getattr(self, entity) for entity in ENTITIES}


def _load_frame_runtime() -> tuple[Any, Any, Any, Any]:
    try:
        from microcosm.frame import Frame, WeightKind, Weights
        from microcosm.frame.adapters.axiom import NZ_SCHEMA
    except ImportError as error:
        raise ImportError(
            "The NZ pilot requires a compatible source checkout of "
            "microcosm-frame with NZ_SCHEMA and AxiomPeriod support."
        ) from error
    return Frame, WeightKind, Weights, NZ_SCHEMA


def _load_dataset_reader() -> Any:
    try:
        from microcosm.frame.adapters.axiom import AxiomEntityTableDataset
    except ImportError as error:
        raise ImportError(
            "The NZ pilot requires Microcosm's Axiom entity-table HDF5 reader."
        ) from error
    return AxiomEntityTableDataset


def _validate_family_nesting(tables: dict[str, pd.DataFrame]) -> None:
    required = {
        "person": ("person_id", "person_household_id", "person_family_id"),
        "household": ("household_id", "household_weight"),
        "family": ("family_id", "family_household_id"),
    }
    for entity, columns in required.items():
        for column in columns:
            if column not in tables[entity]:
                raise ValueError(f"NZ {entity} table is missing {column!r}.")
            if tables[entity][column].isna().any():
                raise ValueError(f"NZ {entity}.{column} must not contain nulls.")
    family = tables["family"]
    if family["family_id"].duplicated().any():
        raise ValueError("NZ family_id values must be unique.")
    membership = tables["person"][
        ["person_family_id", "person_household_id"]
    ].drop_duplicates()
    if membership["person_family_id"].duplicated().any():
        raise ValueError("Each NZ family must belong to exactly one household.")
    expected = family["family_id"].map(
        membership.set_index("person_family_id")["person_household_id"]
    )
    if expected.isna().any() or not np.array_equal(
        expected.to_numpy(), family["family_household_id"].to_numpy()
    ):
        raise ValueError(
            "NZ family_household_id must match the household of every family member."
        )


def frame_from_tables(
    tables: dict[str, pd.DataFrame],
    *,
    allow_effective_weights: bool = False,
    weight_kind: Literal["design", "calibrated"] = "design",
    metadata: Optional[dict[str, Any]] = None,
) -> Any:
    """Validate NZ structure and construct a household-weighted Frame."""
    if set(tables) != set(ENTITIES):
        raise ValueError(f"NZ requires exactly the entity tables {ENTITIES}.")
    copies = {entity: pd.DataFrame(table).copy() for entity, table in tables.items()}
    effective: dict[str, np.ndarray] = {}
    for entity, table in copies.items():
        for column in list(table.columns):
            if not column.endswith("_weight"):
                continue
            owner = column.removesuffix("_weight")
            if owner != entity or (
                owner != "household" and not allow_effective_weights
            ):
                raise ValueError(
                    "NZ household_weight must be the sole stored weight vector."
                )
            if owner != "household":
                effective[owner] = table.pop(column).to_numpy()
    _validate_family_nesting(copies)
    Frame, WeightKind, Weights, schema = _load_frame_runtime()
    values = copies["household"].pop("household_weight").to_numpy()
    person = copies["person"]
    strata = person["support_stratum"] if "support_stratum" in person else None
    frame = Frame(
        copies,
        schema,
        {
            "household": Weights(
                values=values,
                kind=WeightKind.CALIBRATED
                if weight_kind == "calibrated"
                else WeightKind.DESIGN,
            )
        },
        strata,
        metadata=metadata,
    )
    for entity, prior in effective.items():
        resolved = frame.resolve_weights(entity).values
        if not np.array_equal(prior, resolved):
            raise ValueError(
                f"NZ effective {entity}_weight differs from Frame-resolved household weights."
            )
    return frame


def year_data_from_frame(frame: Any) -> NZYearData:
    """Expose Frame-resolved weights through PolicyEngine MicroDataFrames."""
    tables = {}
    for entity in ENTITIES:
        table = frame.table(entity).copy()
        column = f"{entity}_weight"
        table[column] = frame.resolve_weights(entity).values
        tables[entity] = MicroDataFrame(table, weights=column)
    return NZYearData(**tables)


class PopulaceNewZealandDataset(Dataset):
    """A source-only NZ transport input, never a certified country bundle.

    ``year`` is the Microcosm build-period label (2026 for tax year 2026–27).
    ``policy_period`` on outputs carries the explicit Axiom start/end dates.
    This pilot deliberately has no file-writing method; simulation outputs are
    in memory and cannot overwrite the input artifact.
    """

    data: Optional[NZYearData] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    policy_period: Optional[dict[str, str]] = None
    source_sha256: Optional[str] = None
    weight_kind: Literal["design", "calibrated"] = "design"

    def load(self) -> None:
        if self.filepath is None:
            raise ValueError("Cannot load an NZ pilot dataset without a filepath.")
        path = Path(self.filepath)
        before = path.stat()
        digest = sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        source_sha256 = digest.hexdigest()
        if self.source_sha256 is not None and self.source_sha256 != source_sha256:
            raise ValueError("NZ input artifact does not match its expected SHA-256.")
        with pd.HDFStore(path, mode="r") as store:
            keys = {key.lstrip("/") for key in store.keys()}
            if keys != {*ENTITIES, "_time_period"}:
                raise ValueError(
                    "NZ HDF5 must contain person, household, family, and _time_period only."
                )
            period = store["_time_period"]
            if (
                len(period) != 1
                or not pd.api.types.is_integer_dtype(period.dtype)
                or period.iloc[0] != self.year
            ):
                raise ValueError(
                    f"NZ dataset period mismatch: expected build label {self.year}."
                )
            attrs = store.get_storer("_time_period").attrs
            encoded = getattr(attrs, "policyengine_metadata_json", None)
            metadata = (
                json.loads(str(encoded)) if encoded is not None else dict(self.metadata)
            )
            if not isinstance(metadata, dict):
                raise ValueError("NZ dataset metadata must be a JSON object.")
            if self.metadata and self.metadata != metadata:
                raise ValueError("NZ dataset metadata differs from its HDF5 artifact.")
        reader = _load_dataset_reader()(file_path=path)
        if reader.time_period != self.year:
            raise ValueError(
                f"NZ dataset period mismatch: expected build label {self.year}."
            )
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError("NZ input artifact changed while it was being loaded.")
        frame = frame_from_tables(
            reader.tables, weight_kind=self.weight_kind, metadata=metadata
        )
        self.data = year_data_from_frame(frame)
        self.metadata = metadata
        self.source_sha256 = source_sha256

    def to_frame(self) -> Any:
        """Return a fresh validated Frame without redundant effective weights."""
        if self.data is None:
            self.load()
        assert self.data is not None
        return frame_from_tables(
            self.data.entity_data,
            allow_effective_weights=True,
            weight_kind=self.weight_kind,
            metadata=self.metadata,
        )
