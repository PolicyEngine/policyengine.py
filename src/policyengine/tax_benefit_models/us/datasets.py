import json
import warnings
from pathlib import Path
from typing import Any, Optional

import h5py
import pandas as pd
from microdf import MicroDataFrame
from pydantic import ConfigDict, Field

from policyengine.core import Dataset, YearData
from policyengine.provenance.manifest import (
    dataset_logical_name,
    resolve_dataset_reference,
)


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
        """Called after Pydantic initialization."""
        # Make sure we are synchronised between in-memory and storage, at least on initialisation
        if self.data is not None:
            self.save()
        elif self.filepath and not self.data:
            self.load()

    def save(self) -> None:
        """Save dataset to HDF5 file."""
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

    def load(self) -> None:
        """Load dataset from HDF5 file into this instance."""
        filepath = self.filepath
        if _is_policyengine_core_h5(Path(filepath)):
            self.data = _load_policyengine_core_h5(Path(filepath), self.year)
            return

        with pd.HDFStore(filepath, mode="r") as store:
            self.data = USYearData(
                person=MicroDataFrame(store["person"], weights="person_weight"),
                marital_unit=MicroDataFrame(
                    store["marital_unit"], weights="marital_unit_weight"
                ),
                family=MicroDataFrame(store["family"], weights="family_weight"),
                spm_unit=MicroDataFrame(store["spm_unit"], weights="spm_unit_weight"),
                tax_unit=MicroDataFrame(store["tax_unit"], weights="tax_unit_weight"),
                household=MicroDataFrame(
                    store["household"], weights="household_weight"
                ),
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


def _core_h5_variable_entities() -> dict[str, str]:
    from policyengine_us.system import system

    return {name: variable.entity.key for name, variable in system.variables.items()}


def _assign_missing_entity_weights(data: dict[str, pd.DataFrame]) -> None:
    household = data["household"]
    if "household_id" not in household or "household_weight" not in household:
        return

    household_weights = household[["household_id", "household_weight"]]
    person = data["person"]
    if (
        "person_weight" not in person
        and "person_household_id" in person
        and len(person) > 0
    ):
        person.loc[:, "person_weight"] = person["person_household_id"].map(
            household_weights.set_index("household_id")["household_weight"]
        )

    for entity, person_entity_id in US_PERSON_ENTITY_ID_COLUMNS.items():
        if entity == "household":
            continue
        entity_id = US_ENTITY_ID_COLUMNS[entity]
        entity_weight = US_ENTITY_WEIGHT_COLUMNS[entity]
        if (
            entity_weight in data[entity]
            or entity_id not in data[entity]
            or person_entity_id not in person
            or "person_household_id" not in person
        ):
            continue

        entity_households = person[
            [person_entity_id, "person_household_id"]
        ].drop_duplicates(subset=[person_entity_id])
        weight_lookup = entity_households.merge(
            household_weights,
            left_on="person_household_id",
            right_on="household_id",
            how="left",
        ).set_index(person_entity_id)["household_weight"]
        data[entity].loc[:, entity_weight] = data[entity][entity_id].map(weight_lookup)


def _load_policyengine_core_h5(path: Path, year: int) -> USYearData:
    """Load a PolicyEngine core variable/period H5 into .py entity DataFrames."""

    data = {entity: pd.DataFrame() for entity in US_ENTITY_KEYS}
    variable_entities = _core_h5_variable_entities()

    with h5py.File(path, "r") as h5_file:
        entity_lengths = _core_h5_entity_lengths(h5_file, year)
        for variable_name in h5_file.keys():
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


def create_datasets(
    datasets: list[str] = [
        "enhanced_cps_2024",
    ],
    years: list[int] = [2024, 2025, 2026, 2027, 2028],
    data_folder: str = "./data",
) -> dict[str, PolicyEngineUSDataset]:
    """Create PolicyEngineUSDataset instances from logical dataset names or URLs.

    Args:
        datasets: List of logical dataset names or HuggingFace dataset URLs
        years: List of years to extract data for
        data_folder: Directory to save the dataset files

    Returns:
        Dictionary mapping dataset keys (e.g., "enhanced_cps_2024") to PolicyEngineUSDataset objects
    """
    from policyengine_us import Microsimulation

    result = {}
    for dataset in datasets:
        resolved_dataset = resolve_dataset_reference("us", dataset)
        dataset_stem = dataset_logical_name(resolved_dataset)
        sim = Microsimulation(dataset=resolved_dataset)

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

            dataset_key = f"{dataset_stem}_{year}"
            result[dataset_key] = us_dataset

    return result


def load_datasets(
    datasets: list[str] = [
        "enhanced_cps_2024",
    ],
    years: list[int] = [2024, 2025, 2026, 2027, 2028],
    data_folder: str = "./data",
) -> dict[str, PolicyEngineUSDataset]:
    """Load PolicyEngineUSDataset instances from saved HDF5 files.

    Args:
        datasets: List of HuggingFace dataset paths (used to derive file names)
        years: List of years to load data for
        data_folder: Directory containing the dataset files

    Returns:
        Dictionary mapping dataset keys (e.g., "enhanced_cps_2024") to PolicyEngineUSDataset objects
    """
    result = {}
    for dataset in datasets:
        resolved_dataset = resolve_dataset_reference("us", dataset)
        dataset_stem = dataset_logical_name(resolved_dataset)
        for year in years:
            filepath = f"{data_folder}/{dataset_stem}_year_{year}.h5"
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
    path: Path, require_metadata: bool
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
) -> dict[str, PolicyEngineUSDataset]:
    """Load pre-built long-term US projected datasets.

    The country data repo still owns the expensive projection and calibration
    build. This helper lets policyengine.py consume those year-specific H5
    artifacts with sidecar metadata validation.
    """

    result = {}
    root = Path(data_folder).expanduser()
    for year in years:
        path = root / dataset_template.format(year=year)
        if not path.exists():
            raise FileNotFoundError(f"Long-term dataset not found: {path}")

        metadata, metadata_path = _load_dataset_metadata(path, require_metadata)
        if metadata_path is not None:
            validate_long_term_dataset_metadata(
                metadata,
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
            )

        dataset = PolicyEngineUSDataset(
            id=f"{dataset_name}_{year}",
            name=f"{dataset_name}-{year}",
            description=f"US long-term projected dataset for {year}",
            filepath=str(path),
            year=int(year),
            metadata=metadata,
            metadata_filepath=str(metadata_path) if metadata_path else None,
        )
        result[f"{dataset_name}_{year}"] = dataset

    return result


def ensure_datasets(
    datasets: list[str] = [
        "enhanced_cps_2024",
    ],
    years: list[int] = [2024, 2025, 2026, 2027, 2028],
    data_folder: str = "./data",
) -> dict[str, PolicyEngineUSDataset]:
    """Ensure datasets exist, loading if available or creating if not.

    Args:
        datasets: List of HuggingFace dataset paths
        years: List of years to load/create data for
        data_folder: Directory containing or to save the dataset files

    Returns:
        Dictionary mapping dataset keys to PolicyEngineUSDataset objects
    """
    # Check if all dataset files exist
    all_exist = True
    for dataset in datasets:
        resolved_dataset = resolve_dataset_reference("us", dataset)
        dataset_stem = dataset_logical_name(resolved_dataset)
        for year in years:
            filepath = Path(f"{data_folder}/{dataset_stem}_year_{year}.h5")
            if not filepath.exists():
                all_exist = False
                break
        if not all_exist:
            break

    if all_exist:
        return load_datasets(datasets=datasets, years=years, data_folder=data_folder)
    else:
        return create_datasets(datasets=datasets, years=years, data_folder=data_folder)
