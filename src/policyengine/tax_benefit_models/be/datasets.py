"""Belgium pilot dataset: Microcosm entity tables with calibrated weights.

The pilot layout has two entities (person, household), mirroring the
Microcosm ``BE_SCHEMA``. Files are pandas HDF5 stores with ``person``,
``household``, and ``_time_period`` keys. The canonical Microcosm-BE layout
stores calibrated weights once, on the household table; PolicyEngine derives
effective person weights through ``person_household_id`` when loading. Legacy
files may also carry ``person_weight``, but that redundant copy must match the
household weights exactly. Dataset metadata and the optional policy period are
stored as attributes on the ``_time_period`` record so the current
``microcosm.frame`` reader can ignore them while PolicyEngine can round-trip
them.
"""

import json
from pathlib import Path
from typing import Any, ClassVar, Optional

import numpy as np
import pandas as pd
from microdf import MicroDataFrame
from pydantic import ConfigDict, Field

from policyengine.core import Dataset, YearData


def _person_with_household_weights(
    person: pd.DataFrame,
    household: pd.DataFrame,
) -> pd.DataFrame:
    """Return persons with effective weights derived from household weights."""
    person_membership = "person_household_id"
    household_id = "household_id"
    household_weight = "household_weight"
    for table_name, table, required in (
        ("person", person, person_membership),
        ("household", household, household_id),
        ("household", household, household_weight),
    ):
        if required not in table.columns:
            raise ValueError(
                f"Belgium {table_name} table is missing required column {required!r}."
            )
    duplicate_ids = household[household_id].duplicated(keep=False)
    if duplicate_ids.any():
        values = household.loc[duplicate_ids, household_id].drop_duplicates().tolist()
        raise ValueError(f"Belgium household_id values must be unique; found {values}.")
    if household[household_weight].isna().any():
        raise ValueError("Belgium household_weight values must not be null.")

    weight_by_household = household.set_index(household_id)[household_weight]
    derived = person[person_membership].map(weight_by_household)
    if derived.isna().any():
        missing = (
            person.loc[derived.isna(), person_membership].drop_duplicates().tolist()
        )
        raise ValueError(
            "Belgium person_household_id values must resolve to household rows; "
            f"missing {missing}."
        )

    if "person_weight" in person.columns:
        legacy = pd.to_numeric(person["person_weight"], errors="coerce")
        if legacy.isna().any() or not np.array_equal(
            legacy.to_numpy(dtype=float),
            derived.to_numpy(dtype=float),
        ):
            raise ValueError(
                "Legacy Belgium person_weight values do not exactly match the "
                "effective household_weight values."
            )

    result = person.copy()
    result["person_weight"] = derived.to_numpy(copy=True)
    return result


class BEYearData(YearData):
    """Entity-level data for a single Belgian year."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: MicroDataFrame
    household: MicroDataFrame

    @property
    def entity_data(self) -> dict[str, MicroDataFrame]:
        return {"person": self.person, "household": self.household}


class PopulaceBelgiumDataset(Dataset):
    """Belgium pilot dataset loaded from a Microcosm-BE HDF5 artifact.

    ``year`` identifies the input dataset vintage. ``policy_period`` is set on
    derived outputs and identifies the year of law executed by Axiom. Keeping
    both fields prevents a 2025-policy run over a 2026-vintage population from
    being mislabeled as though those were the same period.
    """

    data: Optional[BEYearData] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    policy_period: Optional[int] = None

    _TIME_PERIOD_KEY: ClassVar[str] = "_time_period"
    _METADATA_ATTRIBUTE: ClassVar[str] = "policyengine_metadata_json"
    _POLICY_PERIOD_ATTRIBUTE: ClassVar[str] = "policyengine_policy_period"

    def load(self) -> None:
        if self.filepath is None:
            raise ValueError("Cannot load a Belgium pilot dataset without a filepath.")
        with pd.HDFStore(self.filepath, mode="r") as store:
            person = store["person"]
            household = store["household"]
            if f"/{self._TIME_PERIOD_KEY}" in store.keys():
                stored_year = int(store[self._TIME_PERIOD_KEY].iloc[0])
                if stored_year != self.year:
                    raise ValueError(
                        "Belgium dataset period mismatch: "
                        f"constructor year={self.year}, HDF5 "
                        f"{self._TIME_PERIOD_KEY}={stored_year}."
                    )
                attributes = store.get_storer(self._TIME_PERIOD_KEY).attrs
                metadata_json = getattr(attributes, self._METADATA_ATTRIBUTE, None)
                if metadata_json is not None:
                    stored_metadata = json.loads(str(metadata_json))
                    if self.metadata and self.metadata != stored_metadata:
                        raise ValueError(
                            "Belgium dataset metadata differs from the metadata "
                            "stored in its HDF5 artifact."
                        )
                    self.metadata = stored_metadata
                stored_policy_period = getattr(
                    attributes, self._POLICY_PERIOD_ATTRIBUTE, None
                )
                if stored_policy_period is not None:
                    stored_policy_period = int(stored_policy_period)
                    if (
                        self.policy_period is not None
                        and self.policy_period != stored_policy_period
                    ):
                        raise ValueError(
                            "Belgium dataset policy-period mismatch: "
                            f"constructor policy_period={self.policy_period}, "
                            f"HDF5 policy period={stored_policy_period}."
                        )
                    self.policy_period = stored_policy_period
        person = _person_with_household_weights(person, household)
        self.data = BEYearData(
            person=MicroDataFrame(person, weights="person_weight"),
            household=MicroDataFrame(household, weights="household_weight"),
        )

    def save(self) -> None:
        if self.data is None:
            raise ValueError("No data to save.")
        if self.filepath is None:
            raise ValueError("Cannot save a Belgium pilot dataset without a filepath.")
        # Serialize before opening in mode="w": invalid metadata must not
        # truncate an existing destination.
        metadata_json = json.dumps(
            self.metadata,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        household = pd.DataFrame(self.data.household)
        person = _person_with_household_weights(
            pd.DataFrame(self.data.person),
            household,
        )
        filepath = Path(self.filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with pd.HDFStore(filepath, mode="w") as store:
            # Microcosm carries only explicit entity weights. Person weights
            # are inherited from households and reconstructed on load.
            store["person"] = person.drop(columns=["person_weight"])
            store["household"] = household
            store.put(
                self._TIME_PERIOD_KEY,
                pd.Series([self.year]),
                format="table",
            )
            attributes = store.get_storer(self._TIME_PERIOD_KEY).attrs
            setattr(attributes, self._METADATA_ATTRIBUTE, metadata_json)
            if self.policy_period is not None:
                setattr(
                    attributes,
                    self._POLICY_PERIOD_ATTRIBUTE,
                    int(self.policy_period),
                )
