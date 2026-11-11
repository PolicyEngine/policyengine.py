"""Take a legacy source's SPM independence roles from a certified list.

BACKWARD COMPATIBILITY (#598). policyengine-us counts a 15–17-year-old as an
SPM adult only when ``is_spm_independent_minor_role`` is true; without the
input it falls back to "household head or spouse". A legacy source whose
ASEC/PUF records lack the role leaves Census-built units around an
independent teen without a classified adult.

The certified national release carries a source-backed list of the role for
the same records. :func:`independence_roles` joins it on exactly:

- ASEC/PUF people take the list's role. Every one of them must appear once, in
  the same SPM unit, and the list must name nobody else.
- ACS people take ``is_household_head`` (or a stored
  ``is_household_spouse``), the value the model's own fallback gives them.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .universe import ACS_CHANNEL, NON_ACS_CHANNELS, decode_text, person_link

#: Model input the role is supplied as.
INDEPENDENCE_ROLE = "is_spm_independent_minor_role"

_LIST_COLUMNS = ("person_id", "person_spm_unit_id", "is_spm_independence_role")


def independence_roles(person: pd.DataFrame, list_path: str | Path) -> pd.Series:
    """Return each source person's SPM independence role, by person ID.

    ``person`` is the legacy source's stored person table and ``list_path``
    the hash-verified certified list.

    Raises:
        ValueError: if the source already stores the role, if a person's
            source channel is unknown, or if the list does not match the
            source's ASEC/PUF people exactly.
    """
    if INDEPENDENCE_ROLE in person.columns:
        raise ValueError(
            f"This source stores {INDEPENDENCE_ROLE!r} itself, so it is not a "
            "legacy source for the independence role; remove its "
            "independence_list from the legacy SPM registry."
        )
    unit_link = person_link(person, "spm_unit")
    for column in ("person_id", "person_support_channel"):
        if column not in person.columns:
            raise ValueError(f"The SPM independence role needs person {column!r}.")
    if person["person_id"].duplicated().any():
        raise ValueError("The SPM independence role needs unique person IDs.")

    channel = person["person_support_channel"].map(decode_text)
    is_acs = channel.eq(ACS_CHANNEL).to_numpy()
    is_non_acs = channel.isin(NON_ACS_CHANNELS).to_numpy()
    if not (is_acs | is_non_acs).all():
        raise ValueError("The SPM independence role found unknown source channels.")

    listed = read_independence_list(list_path)
    source_units = person.loc[is_non_acs, ["person_id", unit_link]].set_index(
        "person_id"
    )[unit_link]
    missing = source_units.index.difference(listed.index)
    extra = listed.index.difference(source_units.index)
    if len(missing) or len(extra):
        raise ValueError(
            "The certified SPM independence list does not cover this source's "
            f"ASEC/PUF people exactly: {len(missing)} missing, {len(extra)} not "
            "in the source."
        )
    listed = listed.loc[source_units.index]
    moved = listed["person_spm_unit_id"].to_numpy() != source_units.to_numpy()
    if moved.any():
        raise ValueError(
            f"The certified SPM independence list places {int(moved.sum())} "
            "ASEC/PUF people in a different SPM unit from this source."
        )

    roles = pd.Series(False, index=person["person_id"].to_numpy(), dtype=bool)
    roles.loc[source_units.index] = listed["is_spm_independence_role"].to_numpy(
        dtype=bool
    )
    roles.loc[person.loc[is_acs, "person_id"].to_numpy()] = model_fallback_roles(
        person.loc[is_acs]
    )
    roles.index.name = "person_id"
    return roles


def read_independence_list(path: str | Path) -> pd.DataFrame:
    """Read a certified independence list, refusing any malformed content."""
    listed = pd.read_csv(path, dtype={"is_spm_independence_role": str})
    if tuple(listed.columns) != _LIST_COLUMNS:
        raise ValueError(
            f"Unexpected SPM independence list columns {list(listed.columns)}."
        )
    if listed["person_id"].duplicated().any():
        raise ValueError("The SPM independence list repeats person IDs.")
    roles = listed["is_spm_independence_role"]
    if not roles.isin(["True", "False"]).all():
        raise ValueError("The SPM independence list has non-boolean roles.")
    listed["is_spm_independence_role"] = roles.eq("True")
    return listed.set_index("person_id")


def model_fallback_roles(person: pd.DataFrame) -> np.ndarray:
    """The model's own fallback role: household head or spouse."""
    roles = np.zeros(len(person), dtype=bool)
    for column in ("is_household_head", "is_household_spouse"):
        if column in person.columns:
            values = person[column]
            if values.isna().any():
                raise ValueError(
                    f"The SPM independence role needs complete {column!r}."
                )
            roles |= values.to_numpy(dtype=bool)
    return roles
