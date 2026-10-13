import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from microdf import MicroDataFrame
from pydantic import ConfigDict

from policyengine.core import Dataset, YearData
from policyengine.provenance import year_file_stamp as _shared_stamp
from policyengine.provenance.dataset_materialization import (
    DatasetMaterializationError,
    dataset_source_change,
    dataset_source_identity,
    dataset_source_snapshot,
    is_dataset_source_identity,
    materialize_dataset,
)
from policyengine.provenance.manifest import get_release_manifest
from policyengine.provenance.year_file_stamp import (
    ABSENT,
    NOT_HDF5,
    UNRELATED_TO_CONTENTS,
    is_version_map,
    publish_year_file,
    read_json_dataset,
    read_stored_json,
    source_and_package_differences,
    temporary_year_file,
    write_json_dataset,
    year_file_sources,
)

logger = logging.getLogger(__name__)

#: HDF5 key holding the data year of a UK year file: the year of the observed
#: data the file's tables were projected from (see
#: ``PolicyEngineUKDataset.data_year``). ``create_datasets`` writes it into
#: every year file. Year files written before policyengine.py kept the data
#: year have none: policyengine-uk would take their projected tables as
#: observed data, so ``ensure_datasets`` regenerates them and
#: ``load_datasets`` refuses them (see :func:`year_file_stamp_problem`).
DATA_YEAR_KEY = "data_year"

#: H5 dataset stamping a UK ``create_datasets`` year file, as UTF-8 JSON (see
#: :func:`year_file_stamp`). Its name differs from the US year-file stamp's
#: (``us.legacy_inputs.YEAR_FILE_STAMP_H5_DATASET``), so a year file of one
#: country never passes as one of the other. ``PolicyEngineUKDataset.save()``
#: neither writes nor keeps it, so saving a year file again drops the stamp.
YEAR_FILE_STAMP_H5_DATASET = "policyengine_uk_year_file_stamp"

#: Format revision of UK ``create_datasets`` year files, stored in their
#: stamp (see :func:`year_file_stamp`). Raise it when the stamp changes
#: shape, or when a change to year-file extraction means that files cut
#: before it must be cut again, for a reason the rest of the stamp does not
#: capture.
#:
#: Revision 1 is the first: UK year files cut before it have no stamp, so
#: they are cut again once.
YEAR_FILE_STAMP_REVISION = 1

#: Distributions whose installed versions a UK year file's stamp records.
#: ``create_datasets`` stores each year's tables as policyengine-uk projects
#: the source dataset. policyengine-uk extends a single-year source to later
#: years with ``extend_single_year_dataset``, which uprates each year from the
#: one before by policyengine-uk parameters read through policyengine-core's
#: parameter tree, so either can change a year file's values. (It also draws
#: new student loan holders in each projected year from numpy's random
#: generator, seeded by the year; numpy's version is not recorded.)
YEAR_FILE_PACKAGES = ("policyengine-core", "policyengine-uk")

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

        # Mode "w" truncates the file first, so saving a year file again
        # drops the stamp ``create_datasets`` wrote after it.
        with pd.HDFStore(filepath, mode="w") as store:
            _put_year_data(store, self.data)
            if self.data_year_data is not None:
                _put_year_data(store, self.data_year_data, DATA_YEAR_TABLE_PREFIX)
            # Written last: its presence marks complete tables.
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


def installed_package_versions() -> dict[str, Optional[str]]:
    """Return the installed version of each of :data:`YEAR_FILE_PACKAGES`.

    ``None`` stands for a package that is not installed. The versions come
    from the installed distributions' metadata, so no package is imported.
    """
    return _shared_stamp.installed_package_versions(YEAR_FILE_PACKAGES)


def year_file_stamp(
    source: Mapping[str, Any],
    year: int,
    packages: Optional[Mapping[str, Optional[str]]] = None,
) -> dict[str, Any]:
    """Return the stamp for a UK year file for ``year`` cut now from ``source``.

    ``create_datasets`` writes it to each year file, after the tables and the
    data year, as UTF-8 JSON in :data:`YEAR_FILE_STAMP_H5_DATASET`::

        {"packages": {"policyengine-core": str | null,
                      "policyengine-uk": str | null},
         "revision": int,
         "source": {...},
         "year": int}

    ``source`` is the source dataset's identity (see
    ``policyengine.provenance.dataset_materialization.dataset_source_identity``),
    and ``packages`` defaults to :func:`installed_package_versions`, read
    when this is called (``null`` for a package that is not installed).
    ``revision`` is :data:`YEAR_FILE_STAMP_REVISION`, and ``year`` the year
    whose tables the file holds, so a year file copied or renamed to another
    year's name is not taken for that year.
    """
    if packages is None:
        packages = installed_package_versions()
    return {
        "packages": dict(sorted(packages.items())),
        "revision": YEAR_FILE_STAMP_REVISION,
        "source": dict(source),
        "year": int(year),
    }


def read_year_file_stamp(path: str | Path) -> Any | None:
    """Return the JSON value of a UK year file's stamp, well formed or not.

    ``None`` means the file stores no readable stamp (see
    :data:`YEAR_FILE_STAMP_H5_DATASET`) or is not an H5 file.
    """
    return read_stored_json(path, YEAR_FILE_STAMP_H5_DATASET)


def write_year_file_stamp(path: str | Path, stamp: Mapping[str, Any]) -> None:
    """Stamp a UK year file (see :func:`year_file_stamp`), replacing any stamp."""
    write_json_dataset(path, YEAR_FILE_STAMP_H5_DATASET, dict(stamp))


#: What a run of a year file without a data year would do wrong.
_WITHOUT_A_DATA_YEAR = (
    "policyengine-uk would take its projected tables as observed data and "
    "uprate the State Pension by CPI rather than the triple lock"
)

#: Why an unstamped UK year file without a recorded data year is out of date.
NO_DATA_YEAR = (
    "it has no recorded data year, so it was written before policyengine.py "
    "kept the observed year its tables were projected from, or not written "
    f"completely; {_WITHOUT_A_DATA_YEAR}"
)

#: Why a stamped UK year file without a recorded data year is out of date.
STAMPED_WITHOUT_DATA_YEAR = (
    "it is stamped but records no data year, which every year file "
    f"create_datasets writes records; {_WITHOUT_A_DATA_YEAR}"
)


def year_file_stamp_problem(
    path: str | Path,
    source: Mapping[str, Any],
    year: int,
    packages: Optional[Mapping[str, Optional[str]]] = None,
) -> Optional[str]:
    """Return why a UK ``create_datasets`` year file is out of date, or ``None``.

    ``source`` is the identity of the dataset the year file is requested for
    (see ``policyengine.provenance.dataset_materialization
    .requested_dataset_source_identity``), ``year`` the year it is requested
    for, and ``packages`` defaults to :func:`installed_package_versions`. A
    year file is current only when both of these hold:

    - it records its data year (``DATA_YEAR_KEY``). Without one,
      policyengine-uk would take its projected tables as observed data;
    - its stamp equals ``year_file_stamp(source, year, packages)``: the same
      format revision, year, source identity and package versions. A file cut
      from another revision or file of a dataset that keeps its logical name
      (and so the year file's name) holds the other data, and the package
      versions projected every table in the file.

    Only the stamp and the presence of the data year are read, never the
    tables or the source dataset. A file that cannot be read as HDF5 is out of
    date, and so is one whose stamp or data year is a link that cannot be
    followed. An error that says nothing about the file's contents (no
    permission, a directory, a file another process has locked) is raised
    instead, since the file could not be written again either.

    Returns:
        ``None`` for a current year file; otherwise a clause, starting "it"
        or "its", that says why the file is out of date. It names the source
        it was cut from and the source requested, and the package versions it
        was cut with and those installed, wherever they differ.
    """
    import h5py

    current = year_file_stamp(source, year, packages)
    try:
        with h5py.File(path, "r") as file:
            stamp = read_json_dataset(file, YEAR_FILE_STAMP_H5_DATASET)
            records_data_year = _records_data_year(file)
    except UNRELATED_TO_CONTENTS:
        raise
    except OSError:
        return NOT_HDF5

    # The revision comes first: a later revision may shape its stamp, or
    # record the data year, differently.
    revision = stamp.get("revision") if isinstance(stamp, dict) else None
    if type(revision) is int and revision != YEAR_FILE_STAMP_REVISION:
        return (
            f"it was cut with year-file format revision {revision}, and this "
            f"version of policyengine.py reads only revision "
            f"{YEAR_FILE_STAMP_REVISION}"
        )
    if not records_data_year:
        return NO_DATA_YEAR if stamp is ABSENT else STAMPED_WITHOUT_DATA_YEAR
    if stamp is ABSENT:
        return (
            "it has no stamp of the source dataset and package versions it was "
            "cut from and with, so it was cut by an older policyengine.py or "
            "not written completely"
        )
    # ``type(...) is int`` rather than ``isinstance``: JSON ``true`` loads as
    # ``True``, which equals 1.
    if not (
        isinstance(stamp, dict)
        and set(stamp) == {"packages", "revision", "source", "year"}
        and type(revision) is int
        and type(stamp["year"]) is int
        and is_version_map(stamp["packages"])
        and is_dataset_source_identity(stamp["source"])
    ):
        return "its stamp of what it was cut from and with is malformed"
    if stamp == current:
        return None
    reasons = []
    if stamp["year"] != current["year"]:
        reasons.append(f"it was cut for {stamp['year']}, not {current['year']}")
    reasons.extend(source_and_package_differences(stamp, current))
    return "; ".join(reasons)


def _records_data_year(file: Any) -> bool:
    """Return whether an open H5 year file holds its data year.

    pandas stores the data year (``DATA_YEAR_KEY``) as a group. A node that
    is absent, not a group, or a link that cannot be followed is no data
    year. Errors in ``UNRELATED_TO_CONTENTS`` are raised.
    """
    import h5py

    try:
        # A cycle of soft links, or a chain too long to follow, raises
        # RuntimeError here.
        return isinstance(file.get(DATA_YEAR_KEY), h5py.Group)
    except UNRELATED_TO_CONTENTS:
        raise
    except (KeyError, OSError, RuntimeError):
        return False


def _year_file_sources(
    datasets: list[str], allow_unmanaged: bool = True
) -> list[tuple[str, dict[str, Any]]]:
    """Return each requested dataset's year-file stem and source identity.

    Neither downloads nor reads the source. Raises ``ValueError`` when two of
    them are different sources with one stem, since they would overwrite each
    other's year files (see ``year_file_stamp.year_file_sources``).
    """
    return year_file_sources("uk", datasets, allow_unmanaged)


def create_datasets(
    datasets: Optional[list[str]] = None,
    years: list[int] = [2026, 2027, 2028, 2029, 2030],
    data_folder: str = "./data",
    allow_unmanaged: bool = False,
) -> dict[str, PolicyEngineUKDataset]:
    """Cut UK year files from logical dataset names, URIs or local files.

    Each year file is written to ``{data_folder}/{dataset_stem}_year_{year}.h5``
    with its tables, its data year and, for a year after the data year, the
    data year's tables. Each is stamped with the identity of the source
    dataset it was cut from, the installed policyengine-core and
    policyengine-uk versions, its year and the year-file format revision (see
    :func:`year_file_stamp`), which ``ensure_datasets`` and ``load_datasets``
    check.

    Each year file is written to a temporary file beside its path (see
    ``year_file_stamp.temporary_year_file``). Once a dataset's year files are
    all written, the source is checked again, and only then is each stamped
    and moved onto its path. The tables and the stamp at a year file's path
    therefore always come from one cut, even when two processes cut the same
    year files at once, and a cut that fails leaves the year files already
    there as they were.

    The source file's size and modification time are recorded right after it
    is materialized, and checked again once the year files are written. A
    downloaded file is also hashed again, against the sha256 a bundle
    dataset was verified against or an explicit URI was downloaded with (see
    ``dataset_materialization.dataset_source_change``). Another process can
    replace a file in a shared data folder, for example by materializing
    another release of the same dataset there. If the source changed, no year
    file is moved into place and ``DatasetMaterializationError`` is raised.
    Two requested datasets that are different sources with one stem are
    refused with ``ValueError`` before anything is cut, since they would
    overwrite each other's year files.

    Args:
        datasets: Logical dataset names, Hugging Face URIs or local paths.
            ``None`` selects the certified default dataset.
        years: Years to cut a year file for.
        data_folder: Directory to write the year files (and keep downloaded
            sources) in.
        allow_unmanaged: Allow explicit URIs and local paths that bypass the
            release bundle.

    Returns:
        Dictionary mapping dataset keys (e.g. ``"enhanced_frs_2024_25_2026"``)
        to PolicyEngineUKDataset objects.
    """
    if datasets is not None and len(datasets) > 1:
        _year_file_sources(datasets, allow_unmanaged)

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
        # What each year file is cut from and under: the source, identified
        # before it is loaded, and the package versions.
        identity = dataset_source_identity(source)
        snapshot = dataset_source_snapshot(source)
        packages = installed_package_versions()
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
        # (temporary file, year file, year) for each year file written.
        cut: list[tuple[Path, str, int]] = []
        try:
            for year in years:
                filepath = f"{data_folder}/{dataset_stem}_year_{year}.h5"
                temporary = temporary_year_file(filepath)
                cut.append((temporary, filepath, int(year)))
                uk_dataset = PolicyEngineUKDataset(
                    id=f"{dataset_stem}_year_{year}",
                    name=f"{dataset_stem}-year-{year}",
                    description=f"UK Dataset for year {year} based on {dataset_stem}",
                    filepath=str(temporary),
                    year=int(year),
                    data=_year_data_with_weights(sim.dataset[year]),
                    data_year=data_year,
                    data_year_data=data_year_data if int(year) > data_year else None,
                )
                uk_dataset.save()

                dataset_key = f"{dataset_stem}_{year}"
                result[dataset_key] = uk_dataset

            # Move the year files into place only if the source file is still
            # the one materialized (and, if it was downloaded, still hashes to
            # the sha256 it was verified against or downloaded with), so no
            # stamp names a source the files may not have been cut from.
            change = dataset_source_change(source, identity, snapshot)
            if change is not None:
                raise DatasetMaterializationError(
                    f"The source of the UK year files {data_folder}/"
                    f"{dataset_stem}_year_{{year}}.h5 changed while they were "
                    f"cut: {change}. None of them was written, so "
                    "ensure_datasets() cuts them again."
                )
            # Stamp last, then move each year file onto its path in one step.
            for temporary, filepath, year in cut:
                publish_year_file(
                    temporary,
                    filepath,
                    YEAR_FILE_STAMP_H5_DATASET,
                    year_file_stamp(identity, year, packages),
                )
                result[f"{dataset_stem}_{year}"].filepath = filepath
        finally:
            for temporary, _, _ in cut:
                temporary.unlink(missing_ok=True)

    return result


def load_datasets(
    datasets: Optional[list[str]] = None,
    years: list[int] = [2026, 2027, 2028, 2029, 2030],
    data_folder: str = "./data",
) -> dict[str, PolicyEngineUKDataset]:
    """Load UK year files written by ``create_datasets``.

    A year file is refused unless it records its data year and
    ``create_datasets`` stamped it as cut from the source the dataset
    resolves to now, with the installed policyengine-core and policyengine-uk
    versions and this release's year-file format revision (see
    :func:`year_file_stamp_problem`). A year file without a recorded data
    year was written before policyengine.py kept the observed year its tables
    were projected from: policyengine-uk would take those projected tables as
    observed data and uprate the State Pension by CPI rather than the triple
    lock. A file cut from an earlier release of a dataset the bundle has since
    re-pinned holds that release's data. The error says why, naming the two
    sources or the two package versions. Two requested datasets that are
    different sources with one stem are refused, since they would share year
    files.
    """
    if datasets is None:
        datasets = [get_release_manifest("uk").default_dataset]
    result = {}
    for dataset_stem, source in _year_file_sources(datasets):
        for year in years:
            filepath = f"{data_folder}/{dataset_stem}_year_{year}.h5"
            if Path(filepath).exists():
                problem = year_file_stamp_problem(filepath, source, int(year))
                if problem is not None:
                    raise ValueError(
                        f"UK year file {filepath} is out of date: {problem}. "
                        "Regenerate it with ensure_datasets() or "
                        "create_datasets()."
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

    Existing year files are reused only when they record their data year and
    ``create_datasets`` stamped them as cut from the source each dataset
    resolves to now, with the installed policyengine-core and policyengine-uk
    versions and this release's year-file format revision (see
    :func:`year_file_stamp_problem`). Only each file's stamp and the presence
    of its data year are read to decide, never its tables. The source is
    never downloaded or read: a bundle dataset is identified by its manifest
    entry, an explicit Hugging Face URI by the URI and a local file by its
    file-system metadata (see
    ``dataset_materialization.requested_dataset_source_identity``). If any
    year file is missing or out of date, every year file is created again from
    the source dataset, and each out-of-date file is logged with the reason.
    Two requested datasets that are different sources with one stem are
    refused with ``ValueError``, since they would overwrite each other's year
    files.

    Args:
        datasets: List of logical dataset names, Hugging Face URIs or local
            paths
        years: List of years to load/create data for
        data_folder: Directory containing or to save the dataset files
        allow_unmanaged: Allow explicit URIs and local paths that bypass the
            release bundle, when the year files are created

    Returns:
        Dictionary mapping dataset keys to PolicyEngineUKDataset objects
    """
    if datasets is None:
        datasets = [get_release_manifest("uk").default_dataset]

    # Check that every year file exists and is current. A year file without
    # a data year, or cut from another source or with other package
    # versions, is created again rather than reused.
    all_current = True
    for dataset_stem, source in _year_file_sources(datasets):
        for year in years:
            filepath = Path(f"{data_folder}/{dataset_stem}_year_{year}.h5")
            if not filepath.exists():
                all_current = False
                continue
            problem = year_file_stamp_problem(filepath, source, int(year))
            if problem is not None:
                all_current = False
                logger.warning(
                    "UK year file %s is out of date: %s. Creating the year "
                    "files again.",
                    filepath,
                    problem,
                )

    if all_current:
        return load_datasets(datasets=datasets, years=years, data_folder=data_folder)
    else:
        return create_datasets(
            datasets=datasets,
            years=years,
            data_folder=data_folder,
            allow_unmanaged=allow_unmanaged,
        )
