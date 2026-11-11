"""Derive a legacy source's SPM declarations and hand them to the model.

BACKWARD COMPATIBILITY (#597, #598). The declarations are written as the
ordinary dataset inputs newer sources carry:

- ``spm_unit_spm_universe_status`` (SPM unit, per year): ``INCLUDED`` or
  ``OUTSIDE``;
- ``is_spm_independent_minor_role`` (person): the SPM independence role.

``create_datasets`` stores them as year-file columns
(:func:`add_to_year_file_frames`). A run straight over a legacy source file,
and ``managed_microsimulation``, set them on the simulation instead
(:func:`set_declarations`).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from policyengine.provenance.dataset_materialization import materialize_dataset
from policyengine.tax_benefit_models.us.legacy_inputs import (
    _record_input_variables,
    _simulation_and_branches,
    stored_entity_tables,
)

from .independence import INDEPENDENCE_ROLE, independence_roles
from .model_adapter import UNIVERSE_VARIABLE
from .record import LegacySPMRecord, expected_profile
from .registry import IndependenceListPin, LegacySPMSource
from .universe import (
    NON_ACS_CHANNELS,
    SPMUniverseStatus,
    classify_acs_household_population,
    decode_text,
)

#: Declared statuses a stored scope column may hold.
_DECLARED_STATUSES = frozenset(
    {SPMUniverseStatus.INCLUDED.value, SPMUniverseStatus.OUTSIDE.value}
)


@dataclass(frozen=True)
class LegacySPMDeclarations:
    """The declarations derived for one legacy source."""

    record: LegacySPMRecord
    #: Measurement status by SPM unit ID, if the source needs a scope.
    universe: Optional[pd.Series]
    #: Independence role by person ID, if the source needs one.
    independence_role: Optional[pd.Series]


def derive_declarations(
    source: LegacySPMSource,
    person: pd.DataFrame,
    household: pd.DataFrame,
    *,
    data_dir: Path,
) -> LegacySPMDeclarations:
    """Derive a legacy source's declarations from its stored tables.

    ``data_dir`` is where a certified independence list is downloaded to.
    """
    universe = None
    if source.spm_universe_rule == "acs_household_population":
        universe = classify_acs_household_population(person, household)
    roles = None
    list_people = None
    if source.independence_list is not None:
        list_path = _materialize_independence_list(source.independence_list, data_dir)
        roles = independence_roles(person, list_path)
        channel = person["person_support_channel"].map(decode_text)
        list_people = int(channel.isin(NON_ACS_CHANNELS).sum())
    record = LegacySPMRecord(
        profile=expected_profile(source),
        outside_spm_units=_count(universe, SPMUniverseStatus.OUTSIDE),
        included_spm_units=_count(universe, SPMUniverseStatus.INCLUDED),
        independence_list_people=list_people,
    )
    return LegacySPMDeclarations(
        record=record, universe=universe, independence_role=roles
    )


def derive_from_stored_tables(
    source: LegacySPMSource, dataset: Any, *, data_dir: Path
) -> tuple[LegacySPMDeclarations, list[int]]:
    """Derive declarations from the tables a country Microsimulation loaded.

    Returns the declarations and the dataset years they apply to.
    """
    stored = stored_entity_tables(dataset, {"person": {}, "household": {}})
    if not stored:
        raise ValueError(
            "Legacy SPM declarations need the stored person and household "
            "tables of the source."
        )
    tables = stored[min(stored)]
    declarations = derive_declarations(
        source,
        pd.DataFrame(tables["person"]),
        pd.DataFrame(tables["household"]),
        data_dir=data_dir,
    )
    return declarations, sorted(stored)


def add_to_year_file_frames(
    person: pd.DataFrame, spm_unit: pd.DataFrame, declarations: LegacySPMDeclarations
) -> None:
    """Store the declarations as columns of a year file's tables."""
    if declarations.universe is not None:
        spm_unit[UNIVERSE_VARIABLE] = _align(
            spm_unit["spm_unit_id"], declarations.universe, "SPM units"
        ).astype(object)
    if declarations.independence_role is not None:
        person[INDEPENDENCE_ROLE] = _align(
            person["person_id"], declarations.independence_role, "people"
        ).astype(bool)


def check_year_file_frames(
    person: pd.DataFrame, spm_unit: pd.DataFrame, record: LegacySPMRecord
) -> None:
    """Refuse a year file whose tables lack the declarations it records."""
    source = record.profile.source
    if source.spm_universe_rule is not None:
        if UNIVERSE_VARIABLE not in spm_unit.columns:
            raise ValueError(
                f"This dataset records legacy SPM declarations but stores no "
                f"{UNIVERSE_VARIABLE!r} column. Regenerate it with "
                "ensure_datasets() or create_datasets()."
            )
        statuses = spm_unit[UNIVERSE_VARIABLE].map(decode_text)
        if not statuses.isin(_DECLARED_STATUSES).all():
            raise ValueError(
                f"The stored {UNIVERSE_VARIABLE!r} column must declare every SPM "
                f"unit as one of {sorted(_DECLARED_STATUSES)}."
            )
    if source.independence_list is not None:
        if INDEPENDENCE_ROLE not in person.columns:
            raise ValueError(
                f"This dataset records legacy SPM declarations but stores no "
                f"{INDEPENDENCE_ROLE!r} column. Regenerate it with "
                "ensure_datasets() or create_datasets()."
            )
        roles = person[INDEPENDENCE_ROLE]
        if roles.isna().any() or not pd.api.types.is_bool_dtype(roles.dtype):
            raise ValueError(
                f"The stored {INDEPENDENCE_ROLE!r} column must be complete and boolean."
            )


def set_declarations(
    simulation: Any, declarations: LegacySPMDeclarations, years: Sequence[int]
) -> None:
    """Set the declarations on a built simulation and every branch it has.

    The scope is set for each of ``years``; the role is per person. Values
    are aligned to each simulation's own entity IDs, so a region-scoped
    simulation takes only its own units.
    """
    for country_simulation in _simulation_and_branches(simulation):
        names = []
        if declarations.universe is not None:
            statuses = _align(
                country_simulation.populations["spm_unit"].ids,
                declarations.universe,
                "SPM units",
            ).astype(object)
            for year in years:
                country_simulation.set_input(UNIVERSE_VARIABLE, int(year), statuses)
            names.append(UNIVERSE_VARIABLE)
        if declarations.independence_role is not None:
            roles = _align(
                country_simulation.populations["person"].ids,
                declarations.independence_role,
                "people",
            ).astype(bool)
            country_simulation.set_input(INDEPENDENCE_ROLE, int(years[0]), roles)
            names.append(INDEPENDENCE_ROLE)
        _record_input_variables(country_simulation, names)


def _materialize_independence_list(pin: IndependenceListPin, data_dir: Path) -> Path:
    verified = materialize_dataset(
        "us", pin.bundle_dataset, data_dir=data_dir
    ).bundle_dataset
    if verified is None or verified.sha256 != pin.sha256:
        raise ValueError(
            f"The bundle's {pin.bundle_dataset!r} is not the certified "
            f"{pin.sha256} file the legacy SPM registry pins."
        )
    return Path(verified.path)


def _align(ids: Iterable[Any], values: pd.Series, what: str) -> np.ndarray:
    aligned = pd.Series(np.asarray(ids)).map(values)
    if aligned.isna().any():
        raise ValueError(
            f"Legacy SPM declarations have no value for {int(aligned.isna().sum())} "
            f"{what}."
        )
    return np.asarray(aligned.to_numpy())


def _count(universe: Optional[pd.Series], status: SPMUniverseStatus) -> Optional[int]:
    if universe is None:
        return None
    return int(universe.eq(status.value).sum())
