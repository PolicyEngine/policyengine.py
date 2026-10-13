"""Derive a legacy source's SPM measurement scope from its record types.

BACKWARD COMPATIBILITY (#597). Census's ACS SPM methodology measures the
household population only, so an ACS group-quarters SPM unit is outside the
SPM measurement population. The declaration uses the member names of the
measurement-scope contract newer sources carry (PolicyEngine/microcosm#977):
``INCLUDED`` and ``OUTSIDE``. Nothing here reads age or adult counts.
"""

from __future__ import annotations

from enum import Enum

import numpy as np
import pandas as pd


class SPMUniverseStatus(str, Enum):
    """Whether an SPM unit is inside the SPM measurement population."""

    INCLUDED = "INCLUDED"
    OUTSIDE = "OUTSIDE"
    #: No declaration. Calculations refuse it rather than guess.
    UNRESOLVED = "UNRESOLVED"


ACS_CHANNEL = "acs_2024_1yr"
NON_ACS_CHANNELS = frozenset({"asec", "puf_tax_detail"})

#: ACS household record type (``TYPEHUGQ``) of a housing unit.
ACS_HOUSING_UNIT = 1
#: ACS group-quarters record types (``TYPEHUGQ``) and the relationship code
#: (``RELSHIPP``) each requires: 2 institutional (37), 3 noninstitutional (38).
ACS_GROUP_QUARTERS = {2: 37, 3: 38}


def classify_acs_household_population(
    person: pd.DataFrame, household: pd.DataFrame
) -> pd.Series:
    """Return each SPM unit's measurement status under the ACS household rule.

    ``person`` and ``household`` are the source's stored entity tables. The
    result is indexed by SPM unit ID and holds ``"INCLUDED"`` or
    ``"OUTSIDE"``:

    - ACS records with ``TYPEHUGQ`` 2 or 3 and the matching ``RELSHIPP`` are
      group quarters, so ``OUTSIDE``;
    - ACS housing-unit records (``TYPEHUGQ`` 1, ``RELSHIPP`` not 37 or 38) and
      records from the ``asec`` and ``puf_tax_detail`` channels (no ACS
      record-type evidence at all) are ``INCLUDED``.

    Raises:
        ValueError: if any evidence is missing, unrecognised or inconsistent,
            or if an SPM unit mixes group-quarters and household people.
    """
    unit_link = person_link(person, "spm_unit")
    household_link = person_link(person, "household")
    for column in ("person_support_channel", "RELSHIPP"):
        if column not in person.columns:
            raise ValueError(f"SPM measurement scope needs person {column!r}.")
    for column in ("household_id", "TYPEHUGQ"):
        if column not in household.columns:
            raise ValueError(f"SPM measurement scope needs household {column!r}.")
    if household["household_id"].duplicated().any():
        raise ValueError("SPM measurement scope needs unique household_id values.")
    if not person[household_link].isin(household["household_id"]).all():
        raise ValueError("SPM measurement scope found people with unknown households.")

    channel = person["person_support_channel"].map(decode_text)
    relationship = pd.to_numeric(person["RELSHIPP"], errors="raise")
    record_type = pd.to_numeric(
        person[household_link].map(household.set_index("household_id")["TYPEHUGQ"]),
        errors="raise",
    )

    is_acs = channel.eq(ACS_CHANNEL)
    is_non_acs = channel.isin(NON_ACS_CHANNELS)
    unknown_channel = ~(is_acs | is_non_acs)
    if unknown_channel.any():
        channels = sorted(map(str, channel[unknown_channel].unique()))
        raise ValueError(
            f"SPM measurement scope has no rule for source channels {channels}."
        )

    in_housing_unit = (
        is_acs
        & record_type.eq(ACS_HOUSING_UNIT)
        & relationship.notna()
        & ~relationship.isin(list(ACS_GROUP_QUARTERS.values()))
    )
    in_group_quarters = pd.Series(False, index=person.index)
    for quarters_type, quarters_relationship in ACS_GROUP_QUARTERS.items():
        in_group_quarters |= (
            is_acs
            & record_type.eq(quarters_type)
            & relationship.eq(quarters_relationship)
        )
    recognised_non_acs = is_non_acs & record_type.isna() & relationship.isna()
    unrecognised = ~(in_housing_unit | in_group_quarters | recognised_non_acs)
    if unrecognised.any():
        raise ValueError(
            f"SPM measurement scope cannot classify {int(unrecognised.sum())} "
            "people: their TYPEHUGQ/RELSHIPP evidence is missing or "
            "inconsistent with their source channel."
        )

    group_quarters_by_unit = in_group_quarters.groupby(person[unit_link])
    mixed_units = group_quarters_by_unit.nunique() > 1
    if mixed_units.any():
        raise ValueError(
            f"SPM measurement scope found {int(mixed_units.sum())} SPM units "
            "mixing group-quarters and household people."
        )
    outside = group_quarters_by_unit.first().astype(bool)
    status = pd.Series(
        np.where(
            outside,
            SPMUniverseStatus.OUTSIDE.value,
            SPMUniverseStatus.INCLUDED.value,
        ),
        index=outside.index,
        dtype=object,
    )
    status.index.name = "spm_unit_id"
    return status


def person_link(person: pd.DataFrame, entity: str) -> str:
    """Return the person table's link column to a group entity."""
    for column in (f"person_{entity}_id", f"{entity}_id"):
        if column in person.columns:
            return column
    raise ValueError(f"Legacy SPM declarations need a person {entity} link.")


def decode_text(value: object) -> object:
    return value.decode("utf-8") if isinstance(value, bytes) else value
