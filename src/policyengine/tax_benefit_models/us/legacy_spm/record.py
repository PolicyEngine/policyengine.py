"""Records of the legacy SPM declarations a year file or output was made with.

BACKWARD COMPATIBILITY (#597, #598). A year file cut from a legacy source, and
every output calculated from one, records the :class:`LegacySPMProfile` its
declarations were derived under. The profile is everything that determines
them: the registry entry (source hash, scope rule, independence list hash)
and :data:`ADAPTER_REVISION`. Checks follow the year-file stamp
(``legacy_inputs.year_file_stamp_problem``):

- **total**: any stored value, readable or not, gives either ``None`` or a
  reason, and never raises;
- **exact**: a file is current only when its profile equals the one this
  release derives for its source.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from policyengine.tax_benefit_models.us.legacy_inputs import (
    _ABSENT,
    _UNREADABLE,
    _read_json_dataset,
    _write_json_dataset,
)

from .registry import LegacySPMSource

#: Raise when a change to how declarations are derived or applied means files
#: and outputs made before it must be made again.
ADAPTER_REVISION: Final = 1

#: Key of the record in a US dataset's ``metadata``.
RECORD_KEY: Final = "legacy_spm_declarations"

#: H5 dataset holding the record as UTF-8 JSON in a US file written by
#: ``PolicyEngineUSDataset.save()``.
RECORD_H5_DATASET: Final = "policyengine_legacy_spm_declarations"

#: How a run applied the declarations to the model (see
#: :mod:`.model_adapter`).
ModelModeName = Literal["native", "override"]


class LegacySPMProfile(BaseModel):
    """Everything that determines a legacy source's derived declarations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter_revision: int
    source: LegacySPMSource


class LegacySPMRecord(BaseModel):
    """What a year file or output records about its legacy SPM declarations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    profile: LegacySPMProfile
    #: SPM units the declaration puts outside the SPM measurement.
    outside_spm_units: Optional[int] = Field(default=None, ge=0)
    #: SPM units it puts inside.
    included_spm_units: Optional[int] = Field(default=None, ge=0)
    #: People whose independence role came from the certified list.
    independence_list_people: Optional[int] = Field(default=None, ge=0)
    #: Outputs only: how the run's model applied the declarations.
    model_mode: Optional[ModelModeName] = None


def expected_profile(source: LegacySPMSource) -> LegacySPMProfile:
    """Return the profile this release derives declarations under."""
    return LegacySPMProfile(adapter_revision=ADAPTER_REVISION, source=source)


def parse_record(value: Any) -> Optional[LegacySPMRecord]:
    """Return a stored record as a model, or ``None`` if it is not one."""
    if value is None or value is _ABSENT or value is _UNREADABLE:
        return None
    try:
        return LegacySPMRecord.model_validate(value)
    except ValidationError:
        return None


def record_problem(stored: Any, expected: Optional[LegacySPMProfile]) -> Optional[str]:
    """Return why a stored record does not match ``expected``, or ``None``.

    ``stored`` is a record's JSON value, a record model, or ``_ABSENT``.
    ``expected`` is ``None`` for data whose source needs no legacy
    declarations. The reason is a clause starting "it" or "its".
    """
    if isinstance(stored, LegacySPMRecord):
        stored = stored.model_dump(mode="json")
    if expected is None:
        if stored is _ABSENT:
            return None
        return "it records legacy SPM declarations that its source does not need"
    if stored is _ABSENT:
        return (
            "it has no record of the legacy SPM declarations its source needs, "
            "so it was made by an older policyengine.py or not written completely"
        )
    record = parse_record(stored)
    if record is None:
        return (
            "its record of legacy SPM declarations is unreadable, malformed or "
            "from another version of policyengine.py"
        )
    if record.profile != expected:
        return (
            "its legacy SPM declarations were derived under profile "
            f"{_describe(record.profile)}, and this release derives them under "
            f"{_describe(expected)}"
        )
    return None


def read_record_value(path: str | Path) -> Any:
    """Return the JSON value of a file's record, ``_ABSENT`` or ``_UNREADABLE``.

    Never raises for the file's contents. Errors that say nothing about them
    (no permission, a directory, a lock) are raised, as for the year-file
    stamp.
    """
    import h5py

    try:
        with h5py.File(path, "r") as file:
            return _read_json_dataset(file, RECORD_H5_DATASET)
    except (PermissionError, IsADirectoryError, BlockingIOError):
        raise
    except OSError:
        return _UNREADABLE


def year_file_problem(
    path: str | Path, expected: Optional[LegacySPMProfile]
) -> Optional[str]:
    """Return why a year file's legacy SPM declarations are out of date."""
    return record_problem(read_record_value(path), expected)


def write_record(path: str | Path, record: LegacySPMRecord) -> None:
    """Store a record in an H5 file, replacing any it has."""
    _write_json_dataset(path, RECORD_H5_DATASET, record.model_dump(mode="json"))


def metadata_value(metadata: Mapping[str, Any]) -> Any:
    """Return the record stored in a dataset's ``metadata``, or ``_ABSENT``."""
    return metadata.get(RECORD_KEY, _ABSENT)


def _describe(profile: LegacySPMProfile) -> str:
    source = profile.source
    independence = (
        source.independence_list.sha256[:12] if source.independence_list else None
    )
    return (
        f"(revision {profile.adapter_revision}, source "
        f"{source.source_sha256[:12]}, scope rule {source.spm_universe_rule}, "
        f"independence list {independence})"
    )
