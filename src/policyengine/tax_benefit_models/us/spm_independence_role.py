"""Supply the certified SPM independence role for ACS-local ASEC/PUF records.

#############################################################################
# TEMPORARY ACS-LOCAL SPM INDEPENDENCE ROLE — THIS MUST BE REPLACED.        #
#                                                                           #
# This module patches one certified dataset from another certified          #
# release's file. It is a stopgap, not a data contract: DELETE IT as soon   #
# as a certified ACS-local release stores ``is_spm_independent_minor_role`` #
# for its ASEC/PUF records itself (a rebuild that includes                  #
# PolicyEngine/microcosm#959).                                              #
# Tracking issue: https://github.com/PolicyEngine/policyengine.py/issues/598 #
#############################################################################

policyengine-us counts a 15–17-year-old as an SPM adult only when
``is_spm_independent_minor_role`` is true. The certified ACS-local source
(:data:`~policyengine.tax_benefit_models.us.spm_measurement_scope.ACS_LOCAL_SOURCE_SHA256`)
does not store that role, so the model falls back to "household head or
spouse". Census builds 28 of the source's ASEC/PUF SPM units around an
independent teen who is not the household head; under the fallback those units
have no classified adult and raise ``SPM_COMPOSITION_REQUIRED``.

The same ASEC/PUF records are in the certified national release
``populace-us-2024-spm-20260915``, whose source-backed independence list
(:data:`INDEPENDENCE_LIST`) covers exactly them. :func:`independence_roles`
joins that list onto the source:

- ASEC/PUF people take the list's role. The join must be exact: every one of
  them once, in the same SPM unit, with nobody missing or extra.
- ACS people take ``is_household_head`` (or a stored ``is_household_spouse``),
  which is the value the model's own fallback gives them today.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from policyengine.tax_benefit_models.us.spm_measurement_scope import (
    ACS_CHANNEL,
    NON_ACS_CHANNELS,
)

#: Model input this module supplies.
INDEPENDENCE_ROLE = "is_spm_independent_minor_role"

#: Bundle-manifest entry of the national release's independence list.
INDEPENDENCE_LIST = "source_spm_person_independence"

#: SHA-256 of ``releases/populace-us-2024-spm-20260915/
#: source_spm_person_independence.csv``. The bundle manifest pins the same
#: value; both must agree, so a manifest change cannot swap the list silently.
INDEPENDENCE_LIST_SHA256 = (
    "22b5968d90fecfeef7614583e493fe10cc16bda8b5be82e6f49a5bc2102d3ce5"
)

_LIST_COLUMNS = ("person_id", "person_spm_unit_id", "is_spm_independence_role")


def independence_roles(person: pd.DataFrame, list_path: str | Path) -> pd.Series:
    """Return each source person's SPM independence role, by person ID.

    ``person`` is the ACS-local source's stored person table and
    ``list_path`` the hash-verified national independence list.

    Raises:
        ValueError: if the source already stores the role, if a person's
            source channel is unknown, or if the list does not match the
            source's ASEC/PUF people exactly.
    """
    # TEMPORARY ACS-LOCAL SPM INDEPENDENCE ROLE — THIS MUST BE REPLACED (#598).
    if INDEPENDENCE_ROLE in person.columns:
        raise ValueError(
            f"The ACS-local source now stores {INDEPENDENCE_ROLE!r}; delete "
            "the temporary policyengine.py independence-role patch (#598)."
        )
    unit_link = (
        "person_spm_unit_id" if "person_spm_unit_id" in person else "spm_unit_id"
    )
    for column in ("person_id", unit_link, "person_support_channel"):
        if column not in person.columns:
            raise ValueError(f"The SPM independence role needs person {column!r}.")
    if person["person_id"].duplicated().any():
        raise ValueError("The SPM independence role needs unique person IDs.")

    channel = person["person_support_channel"].map(
        lambda value: value.decode("utf-8") if isinstance(value, bytes) else value
    )
    acs = channel.eq(ACS_CHANNEL).to_numpy()
    non_acs = channel.isin(NON_ACS_CHANNELS).to_numpy()
    if not (acs | non_acs).all():
        raise ValueError("The SPM independence role found unknown source channels.")

    listed = _read_list(list_path)
    source = person.loc[non_acs, ["person_id", unit_link]].set_index("person_id")
    missing = source.index.difference(listed.index)
    extra = listed.index.difference(source.index)
    if len(missing) or len(extra):
        raise ValueError(
            "The national SPM independence list does not cover the ACS-local "
            f"source's ASEC/PUF people exactly: {len(missing)} missing, "
            f"{len(extra)} not in the source."
        )
    listed = listed.loc[source.index]
    moved = listed["person_spm_unit_id"].to_numpy() != source[unit_link].to_numpy()
    if moved.any():
        raise ValueError(
            "The national SPM independence list places "
            f"{int(moved.sum())} ASEC/PUF people in a different SPM unit "
            "from the ACS-local source."
        )

    roles = pd.Series(False, index=person["person_id"].to_numpy(), dtype=bool)
    roles.loc[source.index] = listed["is_spm_independence_role"].to_numpy(dtype=bool)
    roles.loc[person.loc[acs, "person_id"].to_numpy()] = _fallback_roles(
        person.loc[acs]
    )
    roles.index.name = "person_id"
    return roles


def roles_for_people(person_ids, roles: pd.Series) -> np.ndarray:
    """Align roles to a year file's person IDs, refusing unknown people."""
    aligned = pd.Series(np.asarray(person_ids)).map(roles)
    if aligned.isna().any():
        raise ValueError(
            f"The SPM independence role has no value for "
            f"{int(aligned.isna().sum())} people."
        )
    return np.asarray(aligned.to_numpy(dtype=bool))


def _read_list(path: str | Path) -> pd.DataFrame:
    listed = pd.read_csv(path, dtype={"is_spm_independence_role": str})
    if tuple(listed.columns) != _LIST_COLUMNS:
        raise ValueError(
            f"Unexpected SPM independence list columns {list(listed.columns)}."
        )
    if listed["person_id"].duplicated().any():
        raise ValueError("The SPM independence list repeats person IDs.")
    values = listed["is_spm_independence_role"]
    if not values.isin(["True", "False"]).all():
        raise ValueError("The SPM independence list has non-boolean roles.")
    listed["is_spm_independence_role"] = values.eq("True")
    return listed.set_index("person_id")


def _fallback_roles(person: pd.DataFrame) -> np.ndarray:
    """The model's own fallback: household head or spouse."""
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
