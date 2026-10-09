from pathlib import Path
from typing import Optional

import pandas as pd
from microdf import MicroDataFrame
from pydantic import ConfigDict

from policyengine.core import Dataset, YearData
from policyengine.provenance.dataset_materialization import (
    materialize_dataset,
)
from policyengine.provenance.manifest import (
    dataset_logical_name,
    get_release_manifest,
    resolve_dataset_reference,
)

#: HDF5 key holding the data year of a UK year file: the year of the observed
#: data the file's tables were projected from (see
#: ``PolicyEngineUKDataset.data_year``). ``create_datasets`` writes it into
#: every year file. Year files written before policyengine.py kept the data
#: year have none: policyengine-uk would take their projected tables as
#: observed data, so ``ensure_datasets`` regenerates them and
#: ``load_datasets`` refuses them.
DATA_YEAR_KEY = "data_year"

#: Prefix of the HDF5 keys holding the data year's entity tables in a year
#: file whose year comes after its data year.
DATA_YEAR_TABLE_PREFIX = "data_year_"


class UKYearData(YearData):
    """Entity-level data for a single year."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: MicroDataFrame
    benunit: MicroDataFrame
    household: MicroDataFrame

    @property
    def entity_data(self) -> dict[str, MicroDataFrame]:
        """Return a dictionary of entity names to their data."""
        return {
            "person": self.person,
            "benunit": self.benunit,
            "household": self.household,
        }


class PolicyEngineUKDataset(Dataset):
    """UK dataset with multi-year entity-level data."""

    data: Optional[UKYearData] = None

    data_year: Optional[int] = None
    """Year of the observed data that ``data`` was projected from.

    policyengine-uk takes the first year of a dataset as observed data. It
    splits each person's reported State Pension against that year's
    legislated rates and scales the share to the simulated year's rates,
    which follow the triple lock. ``create_datasets`` records the source
    dataset's first year here. ``None`` means ``data`` is itself observed
    data for ``year``, as it is for a dataset built in memory.
    """

    data_year_data: Optional[UKYearData] = None
    """Entity tables of ``data_year``, when it comes before ``year``.

    ``run()`` projects them forward as policyengine-uk does in a direct run,
    and uses ``data`` for ``year`` itself. Without them, policyengine-uk
    would take the projected ``data`` as observed data for ``year`` and the
    State Pension would follow the CPI uprating of its reported amount
    instead of the triple lock.
    """

    def model_post_init(self, __context):
        """Called after Pydantic initialization.

        Constructing with only a ``filepath`` hydrates ``data`` from disk.
        Construction never *writes*: persistence is always explicit via
        ``save()``. Auto-saving on construction (the previous behaviour)
        made an in-memory, region-scoped copy that reused its source's
        ``filepath`` silently truncate the shared dataset file it was
        derived from. See run() in model.py, which now builds scoped
        copies with ``filepath=None``.
        """
        if self.data is None and self.filepath:
            self.load()
        self._check_data_year()

    def _check_data_year(self) -> None:
        """Refuse a data year that cannot be the source of ``year``."""
        if self.data_year is None:
            if self.data_year_data is not None:
                raise ValueError(
                    "PolicyEngineUKDataset has data-year tables but no "
                    "data_year. Set data_year to the year they hold."
                )
            return
        if self.data_year > self.year:
            raise ValueError(
                f"PolicyEngineUKDataset data_year {self.data_year} is after "
                f"its year {self.year}; data can only be projected forward."
            )
        if self.data_year == self.year and self.data_year_data is not None:
            raise ValueError(
                f"PolicyEngineUKDataset year {self.year} is its data year, so "
                "`data` holds the observed tables and data_year_data must be "
                "None."
            )
        # An output records the data year its run anchored on, without the
        # tables.
        if (
            self.data_year < self.year
            and self.data is not None
            and self.data_year_data is None
            and not self.is_output_dataset
        ):
            raise ValueError(
                f"PolicyEngineUKDataset for {self.year} was projected from "
                f"{self.data_year} but has no data_year_data, so "
                "policyengine-uk cannot anchor the State Pension on the "
                "observed year. Pass the data year's tables, or set "
                "data_year=None to treat `data` as observed data."
            )

    def save(self) -> None:
        """Save dataset to HDF5 file.

        Converts object columns to categorical dtype to avoid slow pickle serialization.
        """
        if not self.filepath:
            raise ValueError(
                "Cannot save a PolicyEngineUKDataset with no filepath. This "
                "is an in-memory dataset (e.g. a region-scoped copy); set "
                "`.filepath` to a destination before calling save()."
            )
        filepath = Path(self.filepath)
        if not filepath.parent.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)

        with pd.HDFStore(filepath, mode="w") as store:
            _put_year_data(store, self.data)
            if self.data_year_data is not None:
                _put_year_data(store, self.data_year_data, DATA_YEAR_TABLE_PREFIX)
            # Written last: its presence marks a complete file.
            if self.data_year is not None:
                store.put(DATA_YEAR_KEY, pd.Series([int(self.data_year)]))

    def load(self) -> None:
        """Load dataset from HDF5 file into this instance."""
        filepath = self.filepath
        with pd.HDFStore(filepath, mode="r") as store:
            keys = set(store.keys())
            self.data = _read_year_data(store)
            self.data_year = (
                int(store[DATA_YEAR_KEY].iloc[0])
                if f"/{DATA_YEAR_KEY}" in keys
                else None
            )
            self.data_year_data = (
                _read_year_data(store, DATA_YEAR_TABLE_PREFIX)
                if f"/{DATA_YEAR_TABLE_PREFIX}person" in keys
                else None
            )
        self._check_data_year()

    def __repr__(self) -> str:
        if self.data is None:
            return f"<PolicyEngineUKDataset id={self.id} year={self.year} filepath={self.filepath} (not loaded)>"
        else:
            n_people = len(self.data.person)
            n_benunits = len(self.data.benunit)
            n_households = len(self.data.household)
            return f"<PolicyEngineUKDataset id={self.id} year={self.year} data_year={self.data_year} filepath={self.filepath} people={n_people} benunits={n_benunits} households={n_households}>"


def _put_year_data(store: pd.HDFStore, data: UKYearData, prefix: str = "") -> None:
    """Write one year's entity tables to an open HDF5 store.

    Object columns are stored as categoricals to avoid slow pickle
    serialization; ``format="table"`` supports categorical dtypes.
    """
    for name, frame in data.entity_data.items():
        frame = pd.DataFrame(frame)
        for column in frame.columns:
            if frame[column].dtype == "object":
                frame[column] = frame[column].astype("category")
        store.put(f"{prefix}{name}", frame, format="table")


def _read_year_data(store: pd.HDFStore, prefix: str = "") -> UKYearData:
    """Read one year's entity tables from an open HDF5 store."""
    return UKYearData(
        person=MicroDataFrame(store[f"{prefix}person"], weights="person_weight"),
        benunit=MicroDataFrame(store[f"{prefix}benunit"], weights="benunit_weight"),
        household=MicroDataFrame(
            store[f"{prefix}household"], weights="household_weight"
        ),
    )


def _year_data_with_weights(year_dataset) -> UKYearData:
    """Return a policyengine-uk year's tables with person and benunit weights.

    policyengine-uk stores household weights only; each person and benefit
    unit takes its household's weight.
    """
    # Convert to pandas DataFrames and add weight columns
    person_df = pd.DataFrame(year_dataset.person)
    benunit_df = pd.DataFrame(year_dataset.benunit)
    household_df = pd.DataFrame(year_dataset.household)

    # Map household weights to person and benunit levels
    person_df = person_df.merge(
        household_df[["household_id", "household_weight"]],
        left_on="person_household_id",
        right_on="household_id",
        how="left",
    )
    person_df = person_df.rename(columns={"household_weight": "person_weight"})
    person_df = person_df.drop(columns=["household_id"])

    # Get household_id for each benunit from person table
    benunit_household_map = person_df[
        ["person_benunit_id", "person_household_id"]
    ].drop_duplicates()
    benunit_df = benunit_df.merge(
        benunit_household_map,
        left_on="benunit_id",
        right_on="person_benunit_id",
        how="left",
    )
    benunit_df = benunit_df.merge(
        household_df[["household_id", "household_weight"]],
        left_on="person_household_id",
        right_on="household_id",
        how="left",
    )
    benunit_df = benunit_df.rename(columns={"household_weight": "benunit_weight"})
    benunit_df = benunit_df.drop(
        columns=[
            "person_benunit_id",
            "person_household_id",
            "household_id",
        ],
        errors="ignore",
    )
    return UKYearData(
        person=MicroDataFrame(person_df, weights="person_weight"),
        benunit=MicroDataFrame(benunit_df, weights="benunit_weight"),
        household=MicroDataFrame(household_df, weights="household_weight"),
    )


def _year_file_records_data_year(path: Path) -> bool:
    """Return whether a UK file records its data year (``DATA_YEAR_KEY``).

    A missing or unreadable file raises rather than reading as unrecorded.
    """
    with pd.HDFStore(path, mode="r") as store:
        return f"/{DATA_YEAR_KEY}" in store.keys()


def create_datasets(
    datasets: Optional[list[str]] = None,
    years: list[int] = [2026, 2027, 2028, 2029, 2030],
    data_folder: str = "./data",
    allow_unmanaged: bool = False,
) -> dict[str, PolicyEngineUKDataset]:
    dataset_requests: list[Optional[str]] = [None] if datasets is None else datasets
    result = {}
    for dataset in dataset_requests:
        source = materialize_dataset(
            "uk",
            dataset,
            allow_unmanaged=allow_unmanaged,
            data_dir=Path(data_folder),
        )
        dataset_stem = source.name
        from policyengine_uk import Microsimulation

        sim = Microsimulation(dataset=source.path)
        if not years:
            continue
        # policyengine-uk takes a dataset's first year as observed data and
        # projects the rest from it (see PolicyEngineUKDataset.data_year).
        # Each year file keeps that year and its tables, so a run of the
        # file anchors on the same observed year as a run of the source.
        data_year = int(min(sim.dataset.years))
        data_year_data = _year_data_with_weights(sim.dataset[data_year])
        for year in years:
            uk_dataset = PolicyEngineUKDataset(
                id=f"{dataset_stem}_year_{year}",
                name=f"{dataset_stem}-year-{year}",
                description=f"UK Dataset for year {year} based on {dataset_stem}",
                filepath=f"{data_folder}/{dataset_stem}_year_{year}.h5",
                year=int(year),
                data=_year_data_with_weights(sim.dataset[year]),
                data_year=data_year,
                data_year_data=data_year_data if int(year) > data_year else None,
            )
            uk_dataset.save()

            dataset_key = f"{dataset_stem}_{year}"
            result[dataset_key] = uk_dataset

    return result


def load_datasets(
    datasets: Optional[list[str]] = None,
    years: list[int] = [2026, 2027, 2028, 2029, 2030],
    data_folder: str = "./data",
) -> dict[str, PolicyEngineUKDataset]:
    """Load UK year files written by ``create_datasets``.

    A year file without a recorded data year (``DATA_YEAR_KEY``) was written
    before policyengine.py kept the observed year its tables were projected
    from. policyengine-uk would take those projected tables as observed data
    and uprate the State Pension by CPI rather than the triple lock, so such
    a file is refused.
    """
    if datasets is None:
        datasets = [get_release_manifest("uk").default_dataset]
    result = {}
    for dataset in datasets:
        resolved_dataset = resolve_dataset_reference("uk", dataset)
        dataset_stem = dataset_logical_name(resolved_dataset)
        for year in years:
            filepath = f"{data_folder}/{dataset_stem}_year_{year}.h5"
            if Path(filepath).exists() and not _year_file_records_data_year(
                Path(filepath)
            ):
                raise ValueError(
                    f"UK year file {filepath} has no recorded data year, so it "
                    "was written before policyengine.py kept the observed year "
                    "its tables were projected from. policyengine-uk would "
                    "take the projected tables as observed data and uprate the "
                    "State Pension by CPI rather than the triple lock. "
                    "Regenerate it with ensure_datasets() or create_datasets()."
                )
            # Constructing with a filepath loads the file.
            uk_dataset = PolicyEngineUKDataset(
                name=f"{dataset_stem}-year-{year}",
                description=f"UK Dataset for year {year} based on {dataset_stem}",
                filepath=filepath,
                year=int(year),
            )

            dataset_key = f"{dataset_stem}_{year}"
            result[dataset_key] = uk_dataset

    return result


def ensure_datasets(
    datasets: Optional[list[str]] = None,
    years: list[int] = [2026, 2027, 2028, 2029, 2030],
    data_folder: str = "./data",
    allow_unmanaged: bool = False,
) -> dict[str, PolicyEngineUKDataset]:
    """Ensure datasets exist, loading if available or creating if not.

    Year files without a recorded data year were written before
    policyengine.py kept the observed year their tables were projected from
    (see ``load_datasets``), so they are created again rather than loaded.

    Args:
        datasets: List of HuggingFace dataset paths
        years: List of years to load/create data for
        data_folder: Directory containing or to save the dataset files

    Returns:
        Dictionary mapping dataset keys to PolicyEngineUKDataset objects
    """
    if datasets is None:
        datasets = [get_release_manifest("uk").default_dataset]

    # Check if all dataset files exist
    all_exist = True
    for dataset in datasets:
        resolved_dataset = resolve_dataset_reference("uk", dataset)
        dataset_stem = dataset_logical_name(resolved_dataset)
        for year in years:
            filepath = Path(f"{data_folder}/{dataset_stem}_year_{year}.h5")
            # A year file without a recorded data year would run as observed
            # data, so it is regenerated rather than reused.
            if not filepath.exists() or not _year_file_records_data_year(filepath):
                all_exist = False
                break
        if not all_exist:
            break

    if all_exist:
        return load_datasets(datasets=datasets, years=years, data_folder=data_folder)
    else:
        return create_datasets(
            datasets=datasets,
            years=years,
            data_folder=data_folder,
            allow_unmanaged=allow_unmanaged,
        )
