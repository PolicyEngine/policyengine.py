"""Verified state derivatives of one certified source, not new datasets.

This opt-in prototype is not selected by ``ensure_datasets`` or request serving.
The caller obtains ``MaterializedDataset`` through the installed bundle resolver.
Neither partitioning nor year preparation permits an unmanaged dataset bypass.
"""

from __future__ import annotations

import hashlib
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import h5py
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from policyengine.countries.us.data.states import US_STATE_FIPS
from policyengine.provenance.dataset_materialization import MaterializedDataset
from policyengine.tax_benefit_models.us.datasets import (
    US_ENTITY_KEYS,
    US_PERSON_ENTITY_ID_COLUMNS,
    PolicyEngineUSDataset,
    _prepare_us_year,
    _validate_entity_ids,
)
from policyengine.tax_benefit_models.us.legacy_inputs import (
    apply_legacy_input_renames_to_microsimulation,
)
from policyengine.utils.hashing import sha256_file


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EntityCounts(_StrictModel):
    person: int = Field(ge=0)
    household: int = Field(ge=0)
    tax_unit: int = Field(ge=0)
    spm_unit: int = Field(ge=0)
    family: int = Field(ge=0)
    marital_unit: int = Field(ge=0)


class USStatePartition(_StrictModel):
    format_version: Literal[1] = 1
    parent: MaterializedDataset
    state_code: str
    state_fips: int
    source_year: int
    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(gt=0)
    counts: EntityCounts

    @model_validator(mode="after")
    def validate_state(self) -> USStatePartition:
        if US_STATE_FIPS.get(self.state_code) != self.state_fips:
            raise ValueError("State code and FIPS must identify the same US state/DC")
        return self


class USPartitionManifest(_StrictModel):
    format_version: Literal[1] = 1
    source: MaterializedDataset
    source_year: int
    counts: EntityCounts
    partitions: tuple[USStatePartition, ...]

    @model_validator(mode="after")
    def validate_coverage(self) -> USPartitionManifest:
        if len(self.partitions) != 51 or {p.state_code for p in self.partitions} != set(
            US_STATE_FIPS
        ):
            raise ValueError(
                "Partition manifest must contain all 50 states and DC exactly once"
            )
        for partition in self.partitions:
            if (
                partition.parent != self.source
                or partition.source_year != self.source_year
            ):
                raise ValueError(
                    "Partitions must have the same certified parent and source period"
                )
        for entity in US_ENTITY_KEYS:
            if sum(getattr(p.counts, entity) for p in self.partitions) != getattr(
                self.counts, entity
            ):
                raise ValueError(
                    f"Partition counts do not cover the source {entity} table"
                )
        return self


class USPreparationIdentity(_StrictModel):
    package_versions: dict[str, str]
    code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class USStateYearArtifact(_StrictModel):
    format_version: Literal[1] = 1
    partition: USStatePartition
    year: int = Field(gt=0)
    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(gt=0)
    counts: EntityCounts
    identity: USPreparationIdentity


def _load_native(path: Path) -> tuple[dict[str, pd.DataFrame], int]:
    # Pandas 3 must not re-infer an all-text subset of a stored mixed object
    # column as strings. Keep stored types rather than inferring from state rows.
    with (
        pd.option_context("future.infer_string", False),
        pd.HDFStore(path, "r") as store,
    ):
        frames = {entity: store[entity] for entity in US_ENTITY_KEYS}
        period = store["_time_period"]
    if len(period) != 1 or pd.isna(period.iloc[0]):
        raise ValueError("Native source must declare one nonmissing _time_period")
    year = int(period.iloc[0])
    if year != period.iloc[0]:
        raise ValueError("Native source period must be an integer year")
    return frames, year


def _entity_states(frames: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    """Validate every membership before deriving group state assignments."""
    _validate_entity_ids(frames)
    households = frames["household"]
    if "state_fips" not in households:
        raise ValueError("Missing source household state_fips")
    state = households["state_fips"]
    if state.isna().any() or not state.isin(US_STATE_FIPS.values()).all():
        raise ValueError("Source contains missing or unknown US state_fips")
    lookup = households.set_index("household_id")["state_fips"]
    people = frames["person"]
    household_link = US_PERSON_ENTITY_ID_COLUMNS["household"]
    if household_link not in people:
        raise ValueError(f"Missing {household_link}")
    person_states = people[household_link].map(lookup)
    if person_states.isna().any():
        raise ValueError("Person has a missing or unknown household link")
    if set(people[household_link]) != set(households.household_id):
        raise ValueError("Source includes a household without any person")
    result = {"household": state, "person": person_states}
    for entity in US_ENTITY_KEYS:
        if entity in result:
            continue
        link = US_PERSON_ENTITY_ID_COLUMNS[entity]
        group = frames[entity]
        if link not in people or people[link].isna().any():
            raise ValueError(f"Missing native person {link}")
        if not people[link].isin(group[f"{entity}_id"]).all():
            raise ValueError(f"Unknown native person {link}")
        memberships = pd.DataFrame(
            {"id": people[link], "state": person_states}
        ).drop_duplicates()
        if memberships.id.duplicated().any():
            raise ValueError(f"{entity} spans more than one state")
        group_states = group[f"{entity}_id"].map(memberships.set_index("id").state)
        if group_states.isna().any():
            raise ValueError(f"Source {entity} contains a group without any person")
        result[entity] = group_states
    return result


def _write_partition(
    source_path: Path, path: Path, frames: dict[str, pd.DataFrame]
) -> None:
    with pd.HDFStore(path, "w") as store:
        for entity, frame in frames.items():
            store.put(entity, frame, format="fixed")
    # Copy non-entity HDF nodes and root attributes verbatim: periods and producer
    # metadata must not be reconstructed or stripped during filtering.
    with h5py.File(source_path, "r") as source, h5py.File(path, "a") as output:
        for name in source:
            if name not in US_ENTITY_KEYS:
                source.copy(name, output)
        for name, value in source.attrs.items():
            output.attrs[name] = value
    with (
        pd.option_context("future.infer_string", False),
        pd.HDFStore(path, "r") as store,
    ):
        for entity, expected in frames.items():
            pd.testing.assert_frame_equal(store[entity], expected)


def partition_certified_us_source(
    source: MaterializedDataset, output_dir: Path
) -> USPartitionManifest:
    """Read a hash-verified native source once and write 51 exact state extracts.

    Files are published only after write/read equality. An error removes only
    paths created by this call, never existing cache files or the source.
    """
    if sha256_file(source.path) != source.sha256:
        raise ValueError(
            "Certified source SHA-256 does not match the materialized file"
        )
    frames, year = _load_native(source.path)
    states = _entity_states(frames)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [output_dir / f"state-{code.lower()}.h5" for code in US_STATE_FIPS]
    if any(path.exists() or path.with_suffix(".partial").exists() for path in paths):
        raise FileExistsError("Partition output already exists; refusing to overwrite")
    created: list[Path] = []
    partitions: list[USStatePartition] = []
    try:
        for (code, fips), path in zip(US_STATE_FIPS.items(), paths, strict=True):
            subset = {
                entity: frame.loc[states[entity] == fips]
                for entity, frame in frames.items()
            }
            partial = path.with_suffix(".partial")
            created.append(partial)
            _write_partition(source.path, partial, subset)
            digest = sha256_file(partial)
            partial.rename(path)
            created.append(path)
            partitions.append(
                USStatePartition(
                    parent=source,
                    state_code=code,
                    state_fips=fips,
                    source_year=year,
                    path=path,
                    sha256=digest,
                    bytes=path.stat().st_size,
                    counts=EntityCounts(
                        **{entity: len(frame) for entity, frame in subset.items()}
                    ),
                )
            )
        return USPartitionManifest(
            source=source,
            source_year=year,
            counts=EntityCounts(
                **{entity: len(frame) for entity, frame in frames.items()}
            ),
            partitions=tuple(partitions),
        )
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def prepare_us_state_year(
    partition: USStatePartition, year: int, output_dir: Path
) -> USStateYearArtifact:
    """Run the existing country year preparation on a verified state derivative.

    Input records are passed in memory to the country API, not accepted as an
    arbitrary unmanaged source. The helper also used by national preparation
    retains the installed bundle's SPM selection and legacy input mapping.
    """
    from policyengine_us import Microsimulation
    from policyengine_us.data.dataset_schema import USSingleYearDataset

    from policyengine.tax_benefit_models.us.spm import resolve_spm_selection

    if isinstance(year, bool) or not isinstance(year, int) or year <= 0:
        raise ValueError("Preparation year must be a positive integer")
    if sha256_file(partition.path) != partition.sha256:
        raise ValueError("State partition SHA-256 does not match the file")
    frames, source_year = _load_native(partition.path)
    states = _entity_states(frames)
    if source_year != partition.source_year:
        raise ValueError("Partition source period does not match its manifest")
    if (
        EntityCounts(**{entity: len(frame) for entity, frame in frames.items()})
        != partition.counts
    ):
        raise ValueError("Partition entity counts do not match its manifest")
    if any(not values.eq(partition.state_fips).all() for values in states.values()):
        raise ValueError("Partition includes records from a different state")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"state-{partition.state_code.lower()}-year-{year}.h5"
    partial = path.with_suffix(".partial")
    if path.exists() or partial.exists():
        raise FileExistsError(f"Year output already exists: {path}")
    inputs = USSingleYearDataset(**frames, time_period=source_year)
    sim = Microsimulation(dataset=inputs, spm=resolve_spm_selection())
    renames = apply_legacy_input_renames_to_microsimulation(sim)
    dataset = _prepare_us_year(
        sim,
        year=year,
        dataset_stem=f"state-{partition.state_code.lower()}",
        filepath=partial,
        legacy_input_renames=renames,
    )
    try:
        dataset.save()
        reloaded = PolicyEngineUSDataset(
            name=dataset.name,
            description=dataset.description,
            year=year,
            filepath=str(partial),
        )
        if dataset.data is None or reloaded.data is None:
            raise ValueError("Year preparation did not materialize entity tables")
        for entity, expected in dataset.data.entity_data.items():
            pd.testing.assert_frame_equal(
                pd.DataFrame(reloaded.data.entity_data[entity]), pd.DataFrame(expected)
            )
            if set(expected[f"{entity}_id"]) != set(frames[entity][f"{entity}_id"]):
                raise ValueError(f"Year preparation changed {entity} membership")
        if reloaded.metadata != dataset.metadata:
            raise ValueError("Year output did not preserve its input-rename record")
        artifact = USStateYearArtifact(
            partition=partition,
            year=year,
            path=path,
            sha256=sha256_file(partial),
            bytes=partial.stat().st_size,
            counts=EntityCounts(
                **{
                    entity: len(frame)
                    for entity, frame in dataset.data.entity_data.items()
                }
            ),
            identity=USPreparationIdentity(
                package_versions={
                    name: version(name)
                    for name in (
                        "policyengine",
                        "policyengine-us",
                        "policyengine-core",
                        "spm-calculator",
                    )
                },
                code_sha256=hashlib.sha256(
                    (
                        sha256_file(Path(__file__))
                        + sha256_file(Path(__file__).with_name("datasets.py"))
                    ).encode()
                ).hexdigest(),
            ),
        )
        partial.rename(path)
        return artifact
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
