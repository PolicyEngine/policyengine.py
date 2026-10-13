import hashlib
import importlib.util
import json
import logging
import warnings
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional

import h5py
import pandas as pd
from microdf import MicroDataFrame
from pydantic import ConfigDict, Field

from policyengine.core import Dataset, YearData
from policyengine.provenance.dataset_materialization import (
    DatasetMaterializationError,
    MaterializedDataset,
    dataset_source_change,
    dataset_source_identity,
    dataset_source_snapshot,
    describe_dataset_source_identity,
    materialize_dataset,
    requested_dataset_source_identity,
)
from policyengine.provenance.manifest import (
    dataset_logical_name,
    get_release_manifest,
    resolve_dataset_reference,
)
from policyengine.tax_benefit_models.common.model_version import (
    build_runtime_dataset_provenance,
)
from policyengine.tax_benefit_models.us.legacy_inputs import (
    RENAMES_RECORD_KEY,
    apply_legacy_input_renames_to_microsimulation,
    check_yearly_periods,
    pending_legacy_input_renames,
    read_renames_record,
    write_renames_record,
    write_year_file_stamp,
    year_file_stamp,
    year_file_stamp_problem,
)
from policyengine.utils.hashing import sha256_file

logger = logging.getLogger(__name__)


class USYearData(YearData):
    """Entity-level data for a single year."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: MicroDataFrame
    marital_unit: MicroDataFrame
    family: MicroDataFrame
    spm_unit: MicroDataFrame
    tax_unit: MicroDataFrame
    household: MicroDataFrame

    @property
    def entity_data(self) -> dict[str, MicroDataFrame]:
        """Return a dictionary of entity names to their data."""
        return {
            "person": self.person,
            "marital_unit": self.marital_unit,
            "family": self.family,
            "spm_unit": self.spm_unit,
            "tax_unit": self.tax_unit,
            "household": self.household,
        }


class PolicyEngineUSDataset(Dataset):
    """US dataset with multi-year entity-level data."""

    data: Optional[USYearData] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    metadata_filepath: Optional[str] = None

    def model_post_init(self, __context) -> None:
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

    def save(self) -> None:
        """Save dataset to HDF5 file."""
        if not self.filepath:
            raise ValueError(
                "Cannot save a PolicyEngineUSDataset with no filepath. This "
                "is an in-memory dataset (e.g. a region-scoped copy); set "
                "`.filepath` to a destination before calling save()."
            )
        filepath = Path(self.filepath)
        if not filepath.parent.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=pd.errors.PerformanceWarning,
                message=".*PyTables will pickle object types.*",
            )
            with pd.HDFStore(filepath, mode="w") as store:
                store["person"] = pd.DataFrame(self.data.person)
                store["marital_unit"] = pd.DataFrame(self.data.marital_unit)
                store["family"] = pd.DataFrame(self.data.family)
                store["spm_unit"] = pd.DataFrame(self.data.spm_unit)
                store["tax_unit"] = pd.DataFrame(self.data.tax_unit)
                store["household"] = pd.DataFrame(self.data.household)
        # The renamed stored inputs mapped when this data was cut or
        # calculated. Its presence marks a year file or output as written
        # with the mapping (see ``legacy_inputs.RENAMES_H5_DATASET``).
        renames = self.metadata.get(RENAMES_RECORD_KEY)
        if renames is not None:
            write_renames_record(filepath, renames)

    def load(self) -> None:
        """Load dataset from HDF5 file into this instance."""
        filepath = self.filepath
        path = Path(filepath)
        renames = read_renames_record(path)
        if renames is not None:
            self.metadata[RENAMES_RECORD_KEY] = renames
        if _is_policyengine_core_h5(path):
            self.data = _load_policyengine_core_h5(path, self.year)
            return

        with pd.HDFStore(filepath, mode="r") as store:
            data = {entity: store[entity] for entity in US_ENTITY_KEYS}
        # Native producer files store calibrated household weights. Project
        # missing weights through membership IDs on these in-memory copies,
        # before constructing MicroDataFrames; the source HDF remains read-only.
        _assign_missing_entity_weights(data)
        self.data = USYearData(
            **{
                entity: MicroDataFrame(frame, weights=f"{entity}_weight")
                for entity, frame in data.items()
            }
        )

    def __repr__(self) -> str:
        if self.data is None:
            return f"<PolicyEngineUSDataset id={self.id} year={self.year} filepath={self.filepath} (not loaded)>"
        else:
            n_people = len(self.data.person)
            n_marital_units = len(self.data.marital_unit)
            n_families = len(self.data.family)
            n_spm_units = len(self.data.spm_unit)
            n_tax_units = len(self.data.tax_unit)
            n_households = len(self.data.household)
            return f"<PolicyEngineUSDataset id={self.id} year={self.year} filepath={self.filepath} people={n_people} marital_units={n_marital_units} families={n_families} spm_units={n_spm_units} tax_units={n_tax_units} households={n_households}>"


US_ENTITY_KEYS = (
    "person",
    "household",
    "tax_unit",
    "spm_unit",
    "family",
    "marital_unit",
)

US_ENTITY_ID_COLUMNS = {entity: f"{entity}_id" for entity in US_ENTITY_KEYS}
US_ENTITY_WEIGHT_COLUMNS = {entity: f"{entity}_weight" for entity in US_ENTITY_KEYS}
US_PERSON_ENTITY_ID_COLUMNS = {
    "household": "person_household_id",
    "tax_unit": "person_tax_unit_id",
    "spm_unit": "person_spm_unit_id",
    "family": "person_family_id",
    "marital_unit": "person_marital_unit_id",
}


def _is_policyengine_core_h5(path: Path) -> bool:
    """Return whether ``path`` uses PolicyEngine core's variable/period H5 layout."""

    try:
        with h5py.File(path, "r") as h5_file:
            node = h5_file.get("person_id")
            return isinstance(node, h5py.Group)
    except OSError:
        return False


def _read_core_h5_period_values(
    h5_file: h5py.File,
    variable_name: str,
    year: int,
) -> Any:
    group = h5_file[variable_name]
    period = str(year)
    if period not in group:
        periods = [key for key in group.keys() if key != "ETERNITY"]
        period = sorted(periods)[0] if periods else sorted(group.keys())[0]
    values = group[period][:]
    if getattr(values, "dtype", None) is not None and values.dtype.kind in {"O", "S"}:
        return (
            pd.Series(values)
            .map(
                lambda value: (
                    value.decode("utf-8") if isinstance(value, bytes) else value
                )
            )
            .to_numpy()
        )
    return values


def _core_h5_entity_lengths(h5_file: h5py.File, year: int) -> dict[str, int]:
    lengths: dict[str, int] = {}
    for entity, id_column in US_ENTITY_ID_COLUMNS.items():
        if id_column in h5_file:
            lengths[entity] = len(_read_core_h5_period_values(h5_file, id_column, year))
    return lengths


def _core_h5_variable_entities() -> tuple[dict[str, str], dict[str, str]]:
    """Return each variable's entity, and the pending renames ``{legacy: live}``."""
    from policyengine_us.system import system

    entities = {
        name: variable.entity.key for name, variable in system.variables.items()
    }
    # A stored input the engine has since renamed belongs to its live input's
    # entity. Without this its entity is guessed from its length, and a column
    # as long as two entities is dropped before the rename can map it.
    pending = pending_legacy_input_renames(system.variables)
    for legacy, live in pending.items():
        entities[legacy] = entities[live]
    return entities, pending


def _validate_entity_ids(data: dict[str, pd.DataFrame]) -> None:
    """Reject ambiguous row identities before joining inputs or weights."""
    for entity, frame in data.items():
        entity_id = US_ENTITY_ID_COLUMNS[entity]
        if entity_id not in frame:
            raise ValueError(f"Missing {entity_id} for native entity alignment")
        if frame[entity_id].isna().any() or frame[entity_id].duplicated().any():
            raise ValueError(
                f"Native entity alignment requires unique nonmissing {entity_id} values"
            )


def _assign_missing_entity_weights(data: dict[str, pd.DataFrame]) -> None:
    """Project missing weights from calibrated households through native IDs.

    Both supported HDF layouts use this mapping. Existing weight columns are
    retained; group weights are one household weight, never sums of person
    weights. Missing or ambiguous links cannot silently produce unweighted rows.
    """
    _validate_entity_ids(data)
    missing = [
        entity for entity in US_ENTITY_KEYS if f"{entity}_weight" not in data[entity]
    ]
    if not missing:
        return
    household = data["household"]
    if "household_id" not in household or "household_weight" not in household:
        raise ValueError(
            "Missing household_id or household_weight for deriving entity weights"
        )
    if (
        household["household_id"].isna().any()
        or household["household_id"].duplicated().any()
    ):
        raise ValueError(
            "Deriving entity weights requires unique nonmissing household_id values"
        )
    if household["household_weight"].isna().any():
        raise ValueError(
            "Cannot derive entity weights from missing household_weight values"
        )

    household_weights = household.set_index("household_id")["household_weight"]
    person = data["person"]

    def person_link(entity: str) -> str:
        native = US_PERSON_ENTITY_ID_COLUMNS[entity]
        alias = US_ENTITY_ID_COLUMNS[entity]
        if native in person:
            return native
        if alias in person:
            return alias
        raise ValueError(f"Missing person {native} link for deriving {entity} weights")

    for entity in missing:
        frame = data[entity]
        weight = US_ENTITY_WEIGHT_COLUMNS[entity]
        if frame.empty:
            frame[weight] = pd.Series(index=frame.index, dtype=household_weights.dtype)
            continue
        household_link = person_link("household")
        if entity == "person":
            weights = person[household_link].map(household_weights)
        else:
            entity_id = US_ENTITY_ID_COLUMNS[entity]
            if entity_id not in frame:
                raise ValueError(f"Missing {entity_id} for deriving {weight}")
            entity_link = person_link(entity)
            relationships = person[[entity_link, household_link]].drop_duplicates()
            if relationships[entity_link].duplicated().any():
                raise ValueError(
                    f"Cannot derive {weight}: {entity_id} spans multiple households"
                )
            weight_lookup = relationships.set_index(entity_link)[household_link].map(
                household_weights
            )
            weights = frame[entity_id].map(weight_lookup)
        if weights.isna().any():
            raise ValueError(
                f"Cannot derive {weight}: missing or unknown native household/entity links"
            )
        frame[weight] = weights


def _load_policyengine_core_h5(path: Path, year: int) -> USYearData:
    """Load a PolicyEngine core variable/period H5 into .py entity DataFrames."""

    data = {entity: pd.DataFrame() for entity in US_ENTITY_KEYS}
    variable_entities, pending_renames = _core_h5_variable_entities()

    with h5py.File(path, "r") as h5_file:
        entity_lengths = _core_h5_entity_lengths(h5_file, year)
        for variable_name in h5_file.keys():
            live_name = pending_renames.get(variable_name)
            if live_name is not None and live_name not in h5_file:
                # A stored legacy column is mapped onto every month of the
                # year, so a part-year value is refused, as it is when
                # ``managed_microsimulation`` reads this file. A file that
                # also stores the live name loads that natively, and its
                # legacy column is left alone on both paths.
                node = h5_file[variable_name]
                check_yearly_periods(
                    variable_name,
                    node.keys() if isinstance(node, h5py.Group) else [],
                    path,
                )
            values = _read_core_h5_period_values(h5_file, variable_name, year)
            entity = variable_entities.get(variable_name)
            if entity is None:
                matching_entities = [
                    key
                    for key, length in entity_lengths.items()
                    if length == len(values)
                ]
                if len(matching_entities) != 1:
                    continue
                entity = matching_entities[0]
            if entity not in data:
                continue
            data[entity][variable_name] = values

    _assign_missing_entity_weights(data)

    return USYearData(
        person=MicroDataFrame(data["person"], weights="person_weight"),
        household=MicroDataFrame(data["household"], weights="household_weight"),
        tax_unit=MicroDataFrame(data["tax_unit"], weights="tax_unit_weight"),
        spm_unit=MicroDataFrame(data["spm_unit"], weights="spm_unit_weight"),
        family=MicroDataFrame(data["family"], weights="family_weight"),
        marital_unit=MicroDataFrame(
            data["marital_unit"], weights="marital_unit_weight"
        ),
    )


def _year_file_source(
    dataset: str, allow_unmanaged: bool = True
) -> tuple[str, dict[str, Any]]:
    """Return a requested dataset's year-file stem and its source identity.

    The stem names the year files (``{stem}_year_{year}.h5``) and drops any
    revision, so files cut from every release of a logical dataset share
    names; the identity tells them apart. Neither downloads nor reads the
    source (see ``requested_dataset_source_identity``). A request
    ``materialize_dataset`` would refuse with the same ``allow_unmanaged``
    raises the same error, before the stem is resolved.
    """
    identity = requested_dataset_source_identity(
        "us", dataset, allow_unmanaged=allow_unmanaged
    )
    stem = dataset_logical_name(resolve_dataset_reference("us", dataset))
    return stem, identity


def _year_file_sources(
    datasets: list[str], allow_unmanaged: bool = True
) -> list[tuple[str, dict[str, Any]]]:
    """Return each requested dataset's year-file stem and source identity.

    Raises ``ValueError`` when two of them are different sources with one
    stem. They would write the same year files, each cut overwriting the
    other's, so a request of both would cut them all again every time.
    """
    sources = [_year_file_source(dataset, allow_unmanaged) for dataset in datasets]
    first_by_stem: dict[str, tuple[str, dict[str, Any]]] = {}
    for dataset, (stem, identity) in zip(datasets, sources):
        first, first_identity = first_by_stem.setdefault(stem, (dataset, identity))
        if first_identity != identity:
            raise ValueError(
                f"Datasets {first!r} and {dataset!r} would share the US year "
                f"files {stem}_year_{{year}}.h5, but are different sources: "
                f"{describe_dataset_source_identity(first_identity)} and "
                f"{describe_dataset_source_identity(identity)}. Request them "
                "in separate calls with separate data folders."
            )
    return sources


def create_datasets(
    datasets: Optional[list[str]] = None,
    years: list[int] = [2024, 2025, 2026, 2027, 2028],
    data_folder: str = "./data",
    allow_unmanaged: bool = False,
) -> dict[str, PolicyEngineUSDataset]:
    """Create PolicyEngineUSDataset instances from logical dataset names or URLs.

    Each year file is written to ``{data_folder}/{dataset_stem}_year_{year}.h5``.
    Once a dataset's year files are all written, each is stamped with the
    identity of the source dataset it was cut from, the installed
    policyengine-core and policyengine-us versions, the register of renamed
    stored inputs it was cut under and the year-file format revision (see
    ``legacy_inputs.YEAR_FILE_STAMP_H5_DATASET``), which ``ensure_datasets``
    and ``load_datasets`` check.

    The source file's size and modification time are recorded right after it
    is materialized, and checked again once the year files are written. A
    downloaded file is also hashed again, against the sha256 a bundle
    dataset was verified against or an explicit URI was downloaded with (see
    ``dataset_materialization.dataset_source_change``).
    Another process can replace a file in a shared data folder, for example
    by materializing another release of the same dataset there. If the source
    changed, the year files are left unstamped, so they are cut again, and
    ``DatasetMaterializationError`` is raised. Two requested datasets that are
    different sources with one stem are refused with ``ValueError`` before
    anything is cut, since they would overwrite each other's year files.

    Args:
        datasets: List of logical dataset names or HuggingFace dataset URLs
        years: List of years to extract data for
        data_folder: Directory to save the dataset files

    Returns:
        Dictionary mapping dataset keys (e.g., "populace_us_2024") to PolicyEngineUSDataset objects
    """
    if datasets is not None and len(datasets) > 1:
        _year_file_sources(datasets, allow_unmanaged)

    from policyengine_us import Microsimulation

    from policyengine.tax_benefit_models.us.spm import resolve_spm_selection

    dataset_requests: list[Optional[str]] = datasets or [None]
    result = {}
    for dataset in dataset_requests:
        source = materialize_dataset(
            "us",
            dataset,
            allow_unmanaged=allow_unmanaged,
            data_dir=Path(data_folder),
        )
        dataset_stem = source.name
        # What each year file is cut from and under: the source, identified
        # before it is loaded, the package versions and the register the
        # mapping below uses.
        identity = dataset_source_identity(source)
        snapshot = dataset_source_snapshot(source)
        stamp = year_file_stamp(identity)
        sim = Microsimulation(dataset=source.path, spm=resolve_spm_selection())
        # Map stored inputs the engine has since renamed before extracting,
        # so each year's file stores the live input rather than dropping it.
        legacy_input_renames = apply_legacy_input_renames_to_microsimulation(sim)

        cut: list[PolicyEngineUSDataset] = []
        for year in years:
            # Get all input variables from the simulation
            # We'll calculate each input variable for the specified year
            entity_data = {
                "person": {},
                "household": {},
                "marital_unit": {},
                "family": {},
                "spm_unit": {},
                "tax_unit": {},
            }

            # First, get ID columns which are structural (not input variables)
            # These define entity membership and relationships
            # For person-level links to group entities, use person_X_id naming
            id_variables = {
                "person": [
                    "person_id",
                    "person_household_id",
                    "person_marital_unit_id",
                    "person_family_id",
                    "person_spm_unit_id",
                    "person_tax_unit_id",
                ],
                "household": ["household_id"],
                "marital_unit": ["marital_unit_id"],
                "family": ["family_id"],
                "spm_unit": ["spm_unit_id"],
                "tax_unit": ["tax_unit_id"],
            }

            for entity_key, var_names in id_variables.items():
                for id_var in var_names:
                    if id_var in sim.tax_benefit_system.variables:
                        values = sim.calculate(id_var, period=year).values
                        entity_data[entity_key][id_var] = values

            # Get input variables and calculate them for this year
            for variable_name in sim.input_variables:
                variable = sim.tax_benefit_system.variables[variable_name]
                entity_key = variable.entity.key

                # Calculate the variable for the given year
                values = sim.calculate(variable_name, period=year).values

                # Store in the appropriate entity dictionary
                entity_data[entity_key][variable_name] = values

            # Build entity DataFrames
            person_df = pd.DataFrame(entity_data["person"])
            household_df = pd.DataFrame(entity_data["household"])
            marital_unit_df = pd.DataFrame(entity_data["marital_unit"])
            family_df = pd.DataFrame(entity_data["family"])
            spm_unit_df = pd.DataFrame(entity_data["spm_unit"])
            tax_unit_df = pd.DataFrame(entity_data["tax_unit"])

            # Add weight columns - household weights are primary, map to all entities
            # Person weights = household weights (mapped via person_household_id)
            if "household_weight" in household_df.columns:
                # Only add person_weight if it doesn't already exist
                if "person_weight" not in person_df.columns:
                    person_df = person_df.merge(
                        household_df[["household_id", "household_weight"]],
                        left_on="person_household_id",
                        right_on="household_id",
                        how="left",
                    )
                    person_df = person_df.rename(
                        columns={"household_weight": "person_weight"}
                    )
                    person_df = person_df.drop(
                        columns=["household_id"], errors="ignore"
                    )

                # Map household weights to other group entities via person table
                for entity_name, entity_df, person_id_col, entity_id_col in [
                    (
                        "marital_unit",
                        marital_unit_df,
                        "person_marital_unit_id",
                        "marital_unit_id",
                    ),
                    ("family", family_df, "person_family_id", "family_id"),
                    (
                        "spm_unit",
                        spm_unit_df,
                        "person_spm_unit_id",
                        "spm_unit_id",
                    ),
                    (
                        "tax_unit",
                        tax_unit_df,
                        "person_tax_unit_id",
                        "tax_unit_id",
                    ),
                ]:
                    # Only add entity weight if it doesn't already exist
                    if f"{entity_name}_weight" not in entity_df.columns:
                        # Get household_id for each entity from person table
                        entity_household_map = person_df[
                            [person_id_col, "person_household_id"]
                        ].drop_duplicates()
                        entity_df = entity_df.merge(
                            entity_household_map,
                            left_on=entity_id_col,
                            right_on=person_id_col,
                            how="left",
                        )
                        entity_df = entity_df.merge(
                            household_df[["household_id", "household_weight"]],
                            left_on="person_household_id",
                            right_on="household_id",
                            how="left",
                        )
                        entity_df = entity_df.rename(
                            columns={"household_weight": f"{entity_name}_weight"}
                        )
                        entity_df = entity_df.drop(
                            columns=[
                                "household_id",
                                "person_household_id",
                                person_id_col,
                            ],
                            errors="ignore",
                        )

                    # Update the entity_data
                    if entity_name == "marital_unit":
                        marital_unit_df = entity_df
                    elif entity_name == "family":
                        family_df = entity_df
                    elif entity_name == "spm_unit":
                        spm_unit_df = entity_df
                    elif entity_name == "tax_unit":
                        tax_unit_df = entity_df

            us_dataset = PolicyEngineUSDataset(
                id=f"{dataset_stem}_year_{year}",
                name=f"{dataset_stem}-year-{year}",
                description=f"US Dataset for year {year} based on {dataset_stem}",
                filepath=f"{data_folder}/{dataset_stem}_year_{year}.h5",
                year=int(year),
                metadata={
                    RENAMES_RECORD_KEY: dict(sorted(legacy_input_renames.items()))
                },
                data=USYearData(
                    person=MicroDataFrame(person_df, weights="person_weight"),
                    household=MicroDataFrame(household_df, weights="household_weight"),
                    marital_unit=MicroDataFrame(
                        marital_unit_df, weights="marital_unit_weight"
                    ),
                    family=MicroDataFrame(family_df, weights="family_weight"),
                    spm_unit=MicroDataFrame(spm_unit_df, weights="spm_unit_weight"),
                    tax_unit=MicroDataFrame(tax_unit_df, weights="tax_unit_weight"),
                ),
            )
            us_dataset.save()
            cut.append(us_dataset)

            dataset_key = f"{dataset_stem}_{year}"
            result[dataset_key] = us_dataset

        # Stamp only if the source file is still the one materialized (and,
        # if it was downloaded, still hashes to the sha256 it was verified
        # against or downloaded with), so no stamp names a source the files
        # may not have been cut from.
        change = dataset_source_change(source, identity, snapshot)
        if change is not None:
            raise DatasetMaterializationError(
                f"The source of the US year files {data_folder}/"
                f"{dataset_stem}_year_{{year}}.h5 changed while they were cut: "
                f"{change}. They were left unstamped, so ensure_datasets() "
                "cuts them again."
            )
        # Stamp last. ``save()`` truncates each file first, so a year file
        # whose write stopped part-way has no stamp and is cut again.
        for us_dataset in cut:
            write_year_file_stamp(us_dataset.filepath, stamp)

    return result


def load_datasets(
    datasets: Optional[list[str]] = None,
    years: list[int] = [2024, 2025, 2026, 2027, 2028],
    data_folder: str = "./data",
) -> dict[str, PolicyEngineUSDataset]:
    """Load PolicyEngineUSDataset instances from saved HDF5 files.

    A year file is refused unless ``create_datasets`` stamped it as cut from
    the source the dataset resolves to now, with the installed
    policyengine-core and policyengine-us versions, this release's register of
    renamed stored inputs and its year-file format revision (see
    ``legacy_inputs.year_file_stamp_problem``). A file cut before a register
    entry was added may have lost that input, as files that policyengine.py
    6.1.1 and earlier cut from the certified default lost the WIC take-up
    draw. A file cut from an earlier release of a dataset the bundle has since
    re-pinned holds that release's data. The error says why, naming the
    renames the file may lack, the two sources or the two package versions.
    Two requested datasets that are different sources with one stem are
    refused, since they would share year files.

    Args:
        datasets: List of HuggingFace dataset paths (used to derive file names)
        years: List of years to load data for
        data_folder: Directory containing the dataset files

    Returns:
        Dictionary mapping dataset keys (e.g., "populace_us_2024") to PolicyEngineUSDataset objects
    """
    datasets = datasets or [get_release_manifest("us").default_dataset]
    result = {}
    for dataset_stem, source in _year_file_sources(datasets):
        for year in years:
            filepath = f"{data_folder}/{dataset_stem}_year_{year}.h5"
            if Path(filepath).exists():
                problem = year_file_stamp_problem(filepath, source)
                if problem is not None:
                    raise ValueError(
                        f"US year file {filepath} is out of date: {problem}. "
                        "Regenerate it with ensure_datasets() or "
                        "create_datasets()."
                    )
            us_dataset = PolicyEngineUSDataset(
                name=f"{dataset_stem}-year-{year}",
                description=f"US Dataset for year {year} based on {dataset_stem}",
                filepath=filepath,
                year=year,
            )
            us_dataset.load()

            dataset_key = f"{dataset_stem}_{year}"
            result[dataset_key] = us_dataset

    return result


CALIBRATION_QUALITY_RANK = {
    "aggregate": 0,
    "approximate": 1,
    "exact": 2,
}


def _metadata_path_for_h5(path: Path) -> Path:
    return Path(f"{path}.metadata.json")


def _load_dataset_metadata(
    path: Path,
    require_metadata: bool,
) -> tuple[dict, Optional[Path]]:
    metadata_path = _metadata_path_for_h5(path)
    if not metadata_path.exists():
        if require_metadata:
            raise FileNotFoundError(
                f"Long-term dataset metadata missing for {path}. Expected "
                f"{metadata_path}."
            )
        return {}, None
    return json.loads(metadata_path.read_text(encoding="utf-8")), metadata_path


def _quality_rank(quality: str) -> int:
    try:
        return CALIBRATION_QUALITY_RANK[quality]
    except KeyError as error:
        valid = ", ".join(sorted(CALIBRATION_QUALITY_RANK))
        raise ValueError(
            f"Unknown calibration quality {quality!r}. Valid qualities: {valid}."
        ) from error


def _require_metadata_value(
    metadata: dict,
    path: Path,
    label: str,
    actual: Any,
    expected: Any,
) -> None:
    if expected is None:
        return
    if actual != expected:
        raise ValueError(
            f"Long-term dataset {path} has {label}={actual!r}, expected {expected!r}."
        )


def _policyengine_us_git_sha(policyengine_us_metadata: dict) -> Optional[str]:
    direct_url = policyengine_us_metadata.get("direct_url") or {}
    vcs_info = direct_url.get("vcs_info") or {}
    for key in ("commit_id", "git_commit_id", "vcs_commit_id"):
        value = vcs_info.get(key) or policyengine_us_metadata.get(key)
        if value:
            return str(value)
    return None


def _runtime_policyengine_us_metadata() -> dict[str, Any]:
    try:
        distribution = importlib_metadata.distribution("policyengine-us")
    except importlib_metadata.PackageNotFoundError:
        return {}

    result: dict[str, Any] = {"version": distribution.version}
    direct_url_text = distribution.read_text("direct_url.json")
    if direct_url_text:
        try:
            result["direct_url"] = json.loads(direct_url_text)
        except json.JSONDecodeError:
            result["direct_url"] = {}
    package_file = _runtime_policyengine_us_package_file()
    if package_file is not None:
        result["package_file_sha256"] = sha256_file(package_file)
        result["package_tree_sha256"] = _sha256_directory(package_file.parent)
    return result


def _runtime_policyengine_us_version() -> Optional[str]:
    try:
        return importlib_metadata.version("policyengine-us")
    except importlib_metadata.PackageNotFoundError:
        return None


def _runtime_policyengine_us_package_file() -> Optional[Path]:
    spec = importlib.util.find_spec("policyengine_us")
    if spec is None or spec.origin is None:
        return None
    path = Path(spec.origin)
    return path if path.exists() else None


def _sha256_directory(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        if "__pycache__" in file_path.parts or file_path.suffix in {".pyc", ".pyo"}:
            continue
        relative_path = file_path.relative_to(path).as_posix()
        contents = file_path.read_bytes()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(contents)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(contents)
        digest.update(b"\0")
    return digest.hexdigest()


def _validate_runtime_policyengine_us_match(
    metadata: dict,
    *,
    path: Path,
) -> None:
    policyengine_us = metadata.get("policyengine_us") or {}
    runtime_policyengine_us = _runtime_policyengine_us_metadata()
    metadata_version = policyengine_us.get("version")
    runtime_version = runtime_policyengine_us.get("version")

    if metadata_version and runtime_version != metadata_version:
        raise ValueError(
            f"Long-term dataset {path} was built with policyengine-us "
            f"version {metadata_version!r}, but the installed runtime is "
            f"{runtime_version!r}."
        )

    metadata_git_sha = _policyengine_us_git_sha(policyengine_us)
    runtime_git_sha = _policyengine_us_git_sha(runtime_policyengine_us)
    if metadata_git_sha and runtime_git_sha != metadata_git_sha:
        raise ValueError(
            f"Long-term dataset {path} was built with policyengine-us git SHA "
            f"{metadata_git_sha!r}, but the installed runtime has "
            f"{runtime_git_sha!r}."
        )
    for label in ("package_tree_sha256", "package_file_sha256"):
        metadata_hash = policyengine_us.get(label)
        runtime_hash = runtime_policyengine_us.get(label)
        if metadata_hash and runtime_hash != metadata_hash:
            raise ValueError(
                f"Long-term dataset {path} was built with policyengine-us "
                f"{label} {metadata_hash!r}, but the installed runtime has "
                f"{runtime_hash!r}."
            )


def _validate_runtime_policyengine_us_version(expected_version: Optional[str]) -> None:
    if expected_version is None:
        return
    runtime_version = _runtime_policyengine_us_version()
    if runtime_version != expected_version:
        raise ValueError(
            "Managed long-term datasets require policyengine-us runtime "
            f"version {expected_version!r}, but the installed runtime is "
            f"{runtime_version!r}."
        )


def _managed_long_term_dataset_model_version(manifest: Any) -> Optional[str]:
    certification = getattr(manifest, "certification", None)
    built_with_model_version = getattr(
        certification,
        "built_with_model_version",
        None,
    )
    if built_with_model_version:
        return built_with_model_version
    return manifest.model_package.version


def validate_long_term_dataset_metadata(
    metadata: dict,
    *,
    path: Path,
    year: int,
    required_profile: Optional[str] = None,
    required_target_source: Optional[str] = None,
    required_tax_assumption: Optional[str] = None,
    required_support_augmentation_profile: Optional[str] = None,
    required_support_augmentation_target_year: Optional[int] = None,
    required_support_augmentation_target_year_strategy: Optional[str] = None,
    required_support_augmentation_blueprint_base_weight_scale: Optional[float] = None,
    require_support_augmentation_sanitize_clone_non_target_income: Optional[
        bool
    ] = None,
    require_support_augmentation_sanitize_worker_non_target_income: Optional[
        bool
    ] = None,
    minimum_calibration_quality: Optional[str] = None,
    require_validation_passed: bool = False,
    required_policyengine_us_version: Optional[str] = None,
    required_policyengine_us_git_sha: Optional[str] = None,
    require_policyengine_us_clean_build: bool = False,
    require_runtime_policyengine_us_match: bool = False,
) -> None:
    """Validate sidecar metadata for a long-term projected US dataset."""

    metadata_year = metadata.get("year")
    if metadata_year is not None and int(metadata_year) != int(year):
        raise ValueError(
            f"Long-term dataset {path} metadata year={metadata_year!r}, "
            f"expected {year}."
        )

    profile = metadata.get("profile") or {}
    target_source = metadata.get("target_source") or {}
    tax_assumption = metadata.get("tax_assumption") or {}
    support_augmentation = metadata.get("support_augmentation") or {}
    calibration_audit = metadata.get("calibration_audit") or {}
    policyengine_us = metadata.get("policyengine_us") or {}

    _require_metadata_value(
        metadata,
        path,
        "profile.name",
        profile.get("name"),
        required_profile,
    )
    _require_metadata_value(
        metadata,
        path,
        "target_source.name",
        target_source.get("name"),
        required_target_source,
    )
    _require_metadata_value(
        metadata,
        path,
        "tax_assumption.name",
        tax_assumption.get("name"),
        required_tax_assumption,
    )
    _require_metadata_value(
        metadata,
        path,
        "support_augmentation.name",
        support_augmentation.get("name"),
        required_support_augmentation_profile,
    )
    _require_metadata_value(
        metadata,
        path,
        "support_augmentation.target_year",
        support_augmentation.get("target_year"),
        required_support_augmentation_target_year,
    )
    _require_metadata_value(
        metadata,
        path,
        "support_augmentation.target_year_strategy",
        support_augmentation.get("target_year_strategy"),
        required_support_augmentation_target_year_strategy,
    )
    _require_metadata_value(
        metadata,
        path,
        "support_augmentation.blueprint_base_weight_scale",
        support_augmentation.get("blueprint_base_weight_scale"),
        required_support_augmentation_blueprint_base_weight_scale,
    )
    _require_metadata_value(
        metadata,
        path,
        "support_augmentation.sanitize_clone_non_target_income",
        support_augmentation.get("sanitize_clone_non_target_income"),
        require_support_augmentation_sanitize_clone_non_target_income,
    )
    _require_metadata_value(
        metadata,
        path,
        "support_augmentation.sanitize_worker_non_target_income",
        support_augmentation.get("sanitize_worker_non_target_income"),
        require_support_augmentation_sanitize_worker_non_target_income,
    )

    if minimum_calibration_quality is not None:
        quality = calibration_audit.get("calibration_quality")
        if quality is None:
            raise ValueError(
                f"Long-term dataset {path} is missing "
                "calibration_audit.calibration_quality."
            )
        if _quality_rank(quality) < _quality_rank(minimum_calibration_quality):
            raise ValueError(
                f"Long-term dataset {path} has calibration quality {quality!r}, "
                f"below required minimum {minimum_calibration_quality!r}."
            )

    if (
        require_validation_passed
        and calibration_audit.get("validation_passed") is not True
    ):
        raise ValueError(
            f"Long-term dataset {path} has "
            f"calibration_audit.validation_passed="
            f"{calibration_audit.get('validation_passed')!r}; expected true."
        )

    _require_metadata_value(
        metadata,
        path,
        "policyengine_us.version",
        policyengine_us.get("version"),
        required_policyengine_us_version,
    )
    _require_metadata_value(
        metadata,
        path,
        "policyengine_us.git_sha",
        _policyengine_us_git_sha(policyengine_us),
        required_policyengine_us_git_sha,
    )
    if (
        require_policyengine_us_clean_build
        and policyengine_us.get("git_dirty") is not False
    ):
        raise ValueError(
            f"Long-term dataset {path} has policyengine_us.git_dirty="
            f"{policyengine_us.get('git_dirty')!r}; expected false."
        )
    if require_runtime_policyengine_us_match:
        _validate_runtime_policyengine_us_match(metadata, path=path)


def _long_term_dataset_key(dataset_name: str, year: int) -> str:
    return f"{dataset_name}_{int(year)}"


def _build_long_term_dataset(
    *,
    path: Path,
    year: int,
    dataset_name: str,
    metadata: dict,
    metadata_path: Optional[Path],
    dataset_uri: Optional[str] = None,
    materialized: Optional[MaterializedDataset] = None,
) -> PolicyEngineUSDataset:
    dataset = PolicyEngineUSDataset(
        id=_long_term_dataset_key(dataset_name, year),
        name=f"{dataset_name}-{year}",
        description=f"US long-term projected dataset for {year}",
        filepath=str(path),
        year=int(year),
        metadata=metadata,
        metadata_filepath=str(metadata_path) if metadata_path else None,
    )
    if dataset_uri is not None:
        dataset.metadata.setdefault("policyengine_bundle", {})
        dataset.metadata["policyengine_bundle"].update(
            build_runtime_dataset_provenance(
                dataset_uri,
                str(path),
                materialized,
                logical_name=_long_term_dataset_key(dataset_name, year),
            )
        )
    return dataset


def _validate_loaded_long_term_metadata(
    *,
    metadata: dict,
    metadata_path: Optional[Path],
    path: Path,
    year: int,
    required_profile: Optional[str],
    required_target_source: Optional[str],
    required_tax_assumption: Optional[str],
    required_support_augmentation_profile: Optional[str],
    required_support_augmentation_target_year: Optional[int],
    required_support_augmentation_target_year_strategy: Optional[str],
    required_support_augmentation_blueprint_base_weight_scale: Optional[float],
    require_support_augmentation_sanitize_clone_non_target_income: Optional[bool],
    require_support_augmentation_sanitize_worker_non_target_income: Optional[bool],
    minimum_calibration_quality: Optional[str],
    require_validation_passed: bool,
    required_policyengine_us_version: Optional[str],
    required_policyengine_us_git_sha: Optional[str],
    require_policyengine_us_clean_build: bool,
    require_runtime_policyengine_us_match: bool,
) -> None:
    if metadata_path is None:
        return
    validate_long_term_dataset_metadata(
        metadata,
        path=path,
        year=year,
        required_profile=required_profile,
        required_target_source=required_target_source,
        required_tax_assumption=required_tax_assumption,
        required_support_augmentation_profile=required_support_augmentation_profile,
        required_support_augmentation_target_year=(
            required_support_augmentation_target_year
        ),
        required_support_augmentation_target_year_strategy=(
            required_support_augmentation_target_year_strategy
        ),
        required_support_augmentation_blueprint_base_weight_scale=(
            required_support_augmentation_blueprint_base_weight_scale
        ),
        require_support_augmentation_sanitize_clone_non_target_income=(
            require_support_augmentation_sanitize_clone_non_target_income
        ),
        require_support_augmentation_sanitize_worker_non_target_income=(
            require_support_augmentation_sanitize_worker_non_target_income
        ),
        minimum_calibration_quality=minimum_calibration_quality,
        require_validation_passed=require_validation_passed,
        required_policyengine_us_version=required_policyengine_us_version,
        required_policyengine_us_git_sha=required_policyengine_us_git_sha,
        require_policyengine_us_clean_build=require_policyengine_us_clean_build,
        require_runtime_policyengine_us_match=require_runtime_policyengine_us_match,
    )


def load_long_term_datasets(
    years: list[int],
    data_folder: str = "./projected_datasets",
    dataset_template: str = "{year}.h5",
    dataset_name: str = "long_term_cps",
    require_metadata: bool = True,
    required_profile: Optional[str] = None,
    required_target_source: Optional[str] = None,
    required_tax_assumption: Optional[str] = None,
    required_support_augmentation_profile: Optional[str] = None,
    required_support_augmentation_target_year: Optional[int] = None,
    required_support_augmentation_target_year_strategy: Optional[str] = None,
    required_support_augmentation_blueprint_base_weight_scale: Optional[float] = None,
    require_support_augmentation_sanitize_clone_non_target_income: Optional[
        bool
    ] = None,
    require_support_augmentation_sanitize_worker_non_target_income: Optional[
        bool
    ] = None,
    minimum_calibration_quality: Optional[str] = None,
    require_validation_passed: bool = False,
    required_policyengine_us_version: Optional[str] = None,
    required_policyengine_us_git_sha: Optional[str] = None,
    require_policyengine_us_clean_build: bool = False,
    require_runtime_policyengine_us_match: bool = False,
) -> dict[str, PolicyEngineUSDataset]:
    """Load pre-built long-term US projected datasets.

    The country data repo still owns the expensive projection and calibration
    build. This helper lets policyengine.py consume those year-specific H5
    artifacts with sidecar metadata validation, including optional checks that
    the installed ``policyengine-us`` runtime matches the H5 build metadata.
    """

    result = {}
    root = Path(data_folder).expanduser()
    for year in years:
        path = root / dataset_template.format(year=year)
        if not path.exists():
            raise FileNotFoundError(f"Long-term dataset not found: {path}")

        metadata, metadata_path = _load_dataset_metadata(path, require_metadata)
        _validate_loaded_long_term_metadata(
            metadata=metadata,
            metadata_path=metadata_path,
            path=path,
            year=year,
            required_profile=required_profile,
            required_target_source=required_target_source,
            required_tax_assumption=required_tax_assumption,
            required_support_augmentation_profile=(
                required_support_augmentation_profile
            ),
            required_support_augmentation_target_year=(
                required_support_augmentation_target_year
            ),
            required_support_augmentation_target_year_strategy=(
                required_support_augmentation_target_year_strategy
            ),
            required_support_augmentation_blueprint_base_weight_scale=(
                required_support_augmentation_blueprint_base_weight_scale
            ),
            require_support_augmentation_sanitize_clone_non_target_income=(
                require_support_augmentation_sanitize_clone_non_target_income
            ),
            require_support_augmentation_sanitize_worker_non_target_income=(
                require_support_augmentation_sanitize_worker_non_target_income
            ),
            minimum_calibration_quality=minimum_calibration_quality,
            require_validation_passed=require_validation_passed,
            required_policyengine_us_version=required_policyengine_us_version,
            required_policyengine_us_git_sha=required_policyengine_us_git_sha,
            require_policyengine_us_clean_build=require_policyengine_us_clean_build,
            require_runtime_policyengine_us_match=require_runtime_policyengine_us_match,
        )

        dataset = _build_long_term_dataset(
            path=path,
            year=year,
            dataset_name=dataset_name,
            metadata=metadata,
            metadata_path=metadata_path,
        )
        result[_long_term_dataset_key(dataset_name, year)] = dataset

    return result


def load_managed_long_term_datasets(
    years: list[int],
    dataset_name: str = "long_term_cps",
    data_folder: str = "./data",
    require_metadata: bool = True,
    required_profile: Optional[str] = None,
    required_target_source: Optional[str] = None,
    required_tax_assumption: Optional[str] = None,
    required_support_augmentation_profile: Optional[str] = None,
    required_support_augmentation_target_year: Optional[int] = None,
    required_support_augmentation_target_year_strategy: Optional[str] = None,
    required_support_augmentation_blueprint_base_weight_scale: Optional[float] = None,
    require_support_augmentation_sanitize_clone_non_target_income: Optional[
        bool
    ] = None,
    require_support_augmentation_sanitize_worker_non_target_income: Optional[
        bool
    ] = None,
    minimum_calibration_quality: Optional[str] = None,
    require_validation_passed: bool = False,
    required_policyengine_us_version: Optional[str] = None,
    required_policyengine_us_git_sha: Optional[str] = None,
    require_policyengine_us_clean_build: bool = False,
    require_runtime_policyengine_us_match: bool = True,
) -> dict[str, PolicyEngineUSDataset]:
    """Load bundled long-term US datasets from the managed release manifest.

    Each requested year must have a logical dataset entry named
    ``{dataset_name}_{year}`` in the bundled US manifest. A verified file in
    ``data_folder`` is reused when available; otherwise the exact
    bundle-certified Hugging Face artifact and its certified metadata sidecar
    are downloaded there.
    """

    manifest = get_release_manifest("us")
    if required_policyengine_us_version is None:
        required_policyengine_us_version = _managed_long_term_dataset_model_version(
            manifest
        )
    runtime_policyengine_us_version = manifest.model_package.version
    require_metadata_runtime_match = (
        require_runtime_policyengine_us_match
        and required_policyengine_us_version == runtime_policyengine_us_version
    )

    result = {}
    for year in years:
        key = _long_term_dataset_key(dataset_name, year)
        path_reference = manifest.datasets.get(key)
        if path_reference is None:
            raise ValueError(
                f"Managed long-term dataset {key!r} is not present in the "
                "bundled US release manifest."
            )
        if not path_reference.sha256:
            raise ValueError(
                f"Managed long-term dataset {key!r} is missing a sha256 in "
                "the bundled US release manifest."
            )
        source = materialize_dataset(
            "us",
            key,
            data_dir=Path(data_folder),
        )
        dataset_uri = source.source_uri
        path = Path(source.path)
        metadata, metadata_path = _load_dataset_metadata(path, require_metadata)
        _validate_loaded_long_term_metadata(
            metadata=metadata,
            metadata_path=metadata_path,
            path=path,
            year=year,
            required_profile=required_profile,
            required_target_source=required_target_source,
            required_tax_assumption=required_tax_assumption,
            required_support_augmentation_profile=(
                required_support_augmentation_profile
            ),
            required_support_augmentation_target_year=(
                required_support_augmentation_target_year
            ),
            required_support_augmentation_target_year_strategy=(
                required_support_augmentation_target_year_strategy
            ),
            required_support_augmentation_blueprint_base_weight_scale=(
                required_support_augmentation_blueprint_base_weight_scale
            ),
            require_support_augmentation_sanitize_clone_non_target_income=(
                require_support_augmentation_sanitize_clone_non_target_income
            ),
            require_support_augmentation_sanitize_worker_non_target_income=(
                require_support_augmentation_sanitize_worker_non_target_income
            ),
            minimum_calibration_quality=minimum_calibration_quality,
            require_validation_passed=require_validation_passed,
            required_policyengine_us_version=required_policyengine_us_version,
            required_policyengine_us_git_sha=required_policyengine_us_git_sha,
            require_policyengine_us_clean_build=require_policyengine_us_clean_build,
            require_runtime_policyengine_us_match=require_metadata_runtime_match,
        )
        if require_runtime_policyengine_us_match:
            _validate_runtime_policyengine_us_version(runtime_policyengine_us_version)
        result[key] = _build_long_term_dataset(
            path=path,
            year=year,
            dataset_name=dataset_name,
            metadata=metadata,
            metadata_path=metadata_path,
            dataset_uri=dataset_uri,
            materialized=source.bundle_dataset,
        )

    return result


def ensure_datasets(
    datasets: Optional[list[str]] = None,
    years: list[int] = [2024, 2025, 2026, 2027, 2028],
    data_folder: str = "./data",
    allow_unmanaged: bool = False,
) -> dict[str, PolicyEngineUSDataset]:
    """Ensure datasets exist, loading if available or creating if not.

    Existing year files are reused only when ``create_datasets`` stamped them
    as cut from the source each dataset resolves to now, with the installed
    policyengine-core and policyengine-us versions, this release's register of
    renamed stored inputs and its year-file format revision (see
    ``legacy_inputs.year_file_stamp_problem``). Only each file's stamp and
    renames record are read to decide, never its tables. The source is never
    downloaded or read: a bundle dataset is identified by its manifest entry,
    an explicit Hugging Face URI by the URI and a local file by its
    file-system metadata (see
    ``dataset_materialization.requested_dataset_source_identity``). If any
    year file is missing or out of date, every year file is created again from
    the source dataset, and each out-of-date file is logged with the reason.
    Two requested datasets that are different sources with one stem are
    refused with ``ValueError``, since they would overwrite each other's year
    files.

    Args:
        datasets: List of HuggingFace dataset paths
        years: List of years to load/create data for
        data_folder: Directory containing or to save the dataset files

    Returns:
        Dictionary mapping dataset keys to PolicyEngineUSDataset objects
    """
    datasets = datasets or [get_release_manifest("us").default_dataset]

    # Check that every year file exists and is current. A year file cut
    # from another source, with other package versions or under another
    # register of renamed stored inputs is created again rather than reused.
    all_current = True
    for dataset_stem, source in _year_file_sources(datasets):
        for year in years:
            filepath = Path(f"{data_folder}/{dataset_stem}_year_{year}.h5")
            if not filepath.exists():
                all_current = False
                continue
            problem = year_file_stamp_problem(filepath, source)
            if problem is not None:
                all_current = False
                logger.warning(
                    "US year file %s is out of date: %s. Creating the year "
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
