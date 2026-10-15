"""Decide which legacy SPM declarations a US run needs.

BACKWARD COMPATIBILITY (#597, #598). A run gets its declarations in one of
two ways:

- from a ``create_datasets`` year file, which stores them as columns and
  records the profile they were derived under; or
- straight from a legacy source file (a run over the raw certified file),
  whose stored evidence they are derived from in memory. Such a file is
  recognised by its evidence columns and then its SHA-256, so a file whose
  bytes differ from a certified legacy source gets nothing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from policyengine.tax_benefit_models.us.legacy_inputs import _ABSENT
from policyengine.utils.hashing import sha256_file

from .declarations import (
    LegacySPMDeclarations,
    check_year_file_frames,
    derive_declarations,
)
from .record import (
    LegacySPMProfile,
    LegacySPMRecord,
    expected_profile,
    metadata_value,
    parse_record,
    record_problem,
)
from .registry import LegacySPMSource, legacy_spm_source

#: Columns only a legacy source file (not a year file) stores.
_SOURCE_EVIDENCE = {"person": "person_support_channel", "household": "TYPEHUGQ"}

#: ``{(path, size, mtime_ns): sha256}``, so a file is hashed once per process.
_SHA256_CACHE: dict[tuple[str, int, int], str] = {}


@dataclass(frozen=True)
class LegacySPMRun:
    """The declarations a run applies, and where they come from."""

    record: LegacySPMRecord
    #: Set when they were derived in memory rather than stored as columns.
    in_memory: Optional[LegacySPMDeclarations] = None


def legacy_spm_for_run(dataset: Any) -> Optional[LegacySPMRun]:
    """Return the declarations a run over ``dataset`` must apply.

    Raises:
        ValueError: if the dataset records declarations that are out of
            date, unreadable, or missing from its tables.
    """
    stored = metadata_value(dataset.metadata)
    if stored is not _ABSENT:
        record = parse_record(stored)
        expected = _expected_for_record(record)
        problem = record_problem(stored, expected)
        if problem is not None:
            raise ValueError(
                f"This US dataset is out of date: {problem}. Regenerate it with "
                "ensure_datasets() or create_datasets()."
            )
        assert record is not None
        check_year_file_frames(
            pd.DataFrame(dataset.data.person),
            pd.DataFrame(dataset.data.spm_unit),
            record,
        )
        return LegacySPMRun(record=record)

    source = raw_legacy_source(dataset)
    if source is None:
        return None
    declarations = derive_declarations(
        source,
        pd.DataFrame(dataset.data.person),
        pd.DataFrame(dataset.data.household),
        data_dir=Path(dataset.filepath).parent,
    )
    return LegacySPMRun(record=declarations.record, in_memory=declarations)


def expected_profile_for_dataset(dataset: Any) -> Optional[LegacySPMProfile]:
    """Return the profile a run over ``dataset`` applies, without deriving."""
    stored = metadata_value(getattr(dataset, "metadata", None) or {})
    if stored is not _ABSENT:
        return _expected_for_record(parse_record(stored))
    source = raw_legacy_source(dataset)
    return expected_profile(source) if source is not None else None


def raw_legacy_source(dataset: Any) -> Optional[LegacySPMSource]:
    """Return the legacy source a dataset's file is, if it is one.

    Only a dataset loaded from a file that stores legacy source evidence is
    hashed, and only the first time in a process.
    """
    data = getattr(dataset, "data", None)
    filepath = getattr(dataset, "filepath", None)
    if data is None or not filepath or getattr(dataset, "is_output_dataset", False):
        return None
    for entity, column in _SOURCE_EVIDENCE.items():
        if column not in getattr(data, entity).columns:
            return None
    path = Path(filepath)
    if not path.is_file():
        return None
    status = path.stat()
    key = (os.fspath(path.resolve()), status.st_size, status.st_mtime_ns)
    if key not in _SHA256_CACHE:
        _SHA256_CACHE[key] = sha256_file(path)
    return legacy_spm_source(_SHA256_CACHE[key])


def _expected_for_record(
    record: Optional[LegacySPMRecord],
) -> Optional[LegacySPMProfile]:
    if record is None:
        # Judge it against a profile it cannot match, so it reads as stale.
        return _UNMATCHABLE
    source = legacy_spm_source(record.profile.source.source_sha256)
    return expected_profile(source) if source is not None else None


#: A profile no stored record carries.
_UNMATCHABLE = LegacySPMProfile(
    adapter_revision=-1,
    source=LegacySPMSource(name="<unmatchable>", source_sha256="<unmatchable>"),
)
