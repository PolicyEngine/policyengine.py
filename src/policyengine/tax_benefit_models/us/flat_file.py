"""Run a researcher's own flat file through the pinned US model.

A flat file holds one row per person, as a survey extract does. A simulated
instrument runs the same people through each state's rules, so moving the file
to a state has to carry everything that depends on the state: a stored county or
state label from the old state would otherwise contradict the new ``state_fips``.

``prepare_flat_file`` does that work and checks the file first, because a missing
column does not fail on its own: without ``state_fips`` every household runs as
California. It writes the columns in the one form the pinned loader reads
correctly, ``variable__period``, with each person's groups on their own row.
"""

import logging
from typing import Optional, Union

import numpy as np
import pandas as pd

from policyengine.countries.us.data import US_STATE_FIPS
from policyengine.tax_benefit_models.common.model_version import (
    build_runtime_dataset_provenance,
)

from .model import us_latest
from .spm import SPMSelection, resolve_spm_selection

__all__ = ["flat_file_microsimulation", "prepare_flat_file"]

GROUP_ENTITIES = ("household", "tax_unit", "spm_unit", "family", "marital_unit")
ID_VARIABLES = frozenset(
    {
        "person_id",
        *(f"{group}_id" for group in GROUP_ENTITIES),
        *(f"person_{group}_id" for group in GROUP_ENTITIES),
    }
)
STATE_LABELS = ("state_code", "state_code_str", "state_name")
# Geography finer than a state, which means nothing in another state.
LOCAL_GEOGRAPHY = (
    "block_geoid",
    "cbsa_code",
    "congressional_district_geoid",
    "county",
    "county_fips",
    "county_str",
    "place_fips",
    "puma",
    "sldl",
    "sldu",
    "tract_geoid",
    "vtd",
    "zcta",
    "zip_code",
)
COUNTY_FIPS_LENGTH = 5
ETERNITY = "ETERNITY"
POSTAL_BY_FIPS = {fips: postal for postal, fips in US_STATE_FIPS.items()}
LISTED_COLUMNS = 10


def _variable_of(column: str) -> str:
    """The variable a ``variable__period`` column belongs to."""
    return column.rsplit("__", 1)[0]


def _columns_of(frame: pd.DataFrame, name: str) -> list[str]:
    return [column for column in frame.columns if _variable_of(column) == name]


def _value_at(frame: pd.DataFrame, name: str, year: int) -> Optional[pd.Series]:
    """The column of ``name`` that a run in ``year`` reads, carried forward."""
    readable = []
    for column in _columns_of(frame, name):
        period = column.rsplit("__", 1)[1]
        column_year = year if period == ETERNITY else int(period[:4])
        if column_year <= year:
            readable.append((column_year, column))
    return frame[max(readable)[1]] if readable else None


def _with_periods(people: pd.DataFrame, year: int) -> pd.DataFrame:
    """Name every column ``variable__period``, as the pinned loader expects."""
    frame = people.rename(
        columns=lambda column: (
            str(column) if "__" in str(column) else f"{column}__{year}"
        )
    )
    repeated = frame.columns[frame.columns.duplicated()].unique().tolist()
    if repeated:
        raise ValueError(
            f"The file gives {', '.join(repeated)} more than once. Keep one column "
            "for each variable and period."
        )
    return frame


def _without_unknown_columns(frame: pd.DataFrame, variables) -> pd.DataFrame:
    """Drop columns the model cannot read, and say so."""
    unknown = [
        column for column in frame.columns if _variable_of(column) not in variables
    ]
    if unknown:
        listed = ", ".join(unknown[:LISTED_COLUMNS])
        more = len(unknown) - LISTED_COLUMNS
        logging.warning(
            f"The run ignores {len(unknown)} column(s) that name no PolicyEngine "
            f"variable: {listed}{f' and {more} more' if more > 0 else ''}."
        )
    return frame.drop(columns=unknown)


def _id_values(values: pd.Series, name: str) -> pd.Series:
    """IDs as integers, the only form the model stores."""
    if values.isna().any():
        raise ValueError(f"{name} has blanks. Every row needs one.")
    if pd.api.types.is_integer_dtype(values):
        return values.astype("int64")
    return pd.Series(pd.factorize(values, sort=True)[0], index=values.index)


def _with_person_level_ids(frame: pd.DataFrame, year: int) -> pd.DataFrame:
    """Put each person's ID and group memberships on their own row."""
    memberships = {}
    for group in GROUP_ENTITIES:
        columns = _columns_of(frame, f"person_{group}_id") or _columns_of(
            frame, f"{group}_id"
        )
        if columns:
            memberships[group] = _id_values(frame[columns[0]], f"{group}_id")
    missing = [group for group in GROUP_ENTITIES if group not in memberships]
    if missing:
        names = ", ".join(f"{group}_id" for group in missing)
        raise ValueError(
            f"The file has no {names}. A flat file needs one of these on every "
            "person's row to say who belongs together."
        )

    person_columns = _columns_of(frame, "person_id")
    if person_columns:
        persons = _id_values(frame[person_columns[0]], "person_id")
        if persons.duplicated().any():
            raise ValueError("person_id repeats. A flat file holds one row per person.")
    else:
        persons = pd.Series(np.arange(len(frame)), index=frame.index)

    frame = frame.drop(
        columns=[
            column for column in frame.columns if _variable_of(column) in ID_VARIABLES
        ]
    )
    identifiers = {f"person_id__{year}": persons}
    for group, ids in memberships.items():
        identifiers[f"person_{group}_id__{year}"] = ids
    return frame.assign(**identifiers)


def _county_text(value) -> str:
    """A county FIPS code as five-digit text, or blank for no county.

    ``read_csv`` turns 06037 into 6037, or 6037.0 next to a blank.
    """
    if pd.isna(value) or value == "":
        return ""
    if isinstance(value, bytes):
        value = value.decode()
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        value = int(value)
    text = str(value).strip()
    if not text.isdigit() or len(text) > COUNTY_FIPS_LENGTH:
        raise ValueError(f"county_fips holds {value!r}, which is no county FIPS code.")
    return text.zfill(COUNTY_FIPS_LENGTH)


def _with_text_counties(frame: pd.DataFrame) -> pd.DataFrame:
    counties = {
        column: frame[column].map(_county_text)
        for column in _columns_of(frame, "county_fips")
    }
    return frame.assign(**counties)


def _state_fips(state: Union[str, int]) -> int:
    """Read a postal code or a FIPS code as a FIPS code."""
    if isinstance(state, str) and state.upper() in US_STATE_FIPS:
        return US_STATE_FIPS[state.upper()]
    if state in POSTAL_BY_FIPS:
        return int(state)
    raise ValueError(f"{state!r} is neither a state postal code nor a state FIPS code.")


def _in_state(frame: pd.DataFrame, fips: int, year: int) -> pd.DataFrame:
    """Move every household to one state, in every year the file holds."""
    frame = frame.drop(
        columns=[
            column
            for column in frame.columns
            if _variable_of(column) in {*STATE_LABELS, *LOCAL_GEOGRAPHY}
        ]
    )
    state_columns = {f"state_fips__{year}", *_columns_of(frame, "state_fips")}
    return frame.assign(**dict.fromkeys(state_columns, fips))


def _require_coherent_geography(frame: pd.DataFrame, year: int) -> None:
    """Check a file that keeps its own states, since nothing moves them here."""
    state = _value_at(frame, "state_fips", year)
    if state is None:
        raise ValueError(
            f"The file has no state_fips for {year}, so every household would run "
            "as California. Add the column, or pass state= to run them all in one "
            "state."
        )
    unknown = set(state.unique()) - set(POSTAL_BY_FIPS)
    if unknown:
        listed = ", ".join(sorted(str(value) for value in unknown))
        raise ValueError(f"state_fips holds {listed}, which name no state.")

    households = frame[f"person_household_id__{year}"]
    if state.groupby(households).nunique().gt(1).any():
        raise ValueError("Some households span several values of state_fips.")

    county = _value_at(frame, "county_fips", year)
    if county is not None:
        known = county != ""
        if county[known].str[:2].astype(int).ne(state[known]).any():
            raise ValueError(
                "Some rows hold a county_fips outside their state_fips. Correct them, "
                "or pass state= to run the file in one state, which clears county."
            )

    postal = state.map(POSTAL_BY_FIPS)
    for label in STATE_LABELS:
        stored = _value_at(frame, label, year)
        if stored is not None and stored.astype(str).ne(postal).any():
            raise ValueError(
                f"Some rows hold a {label} that disagrees with state_fips. Correct "
                "them, or pass state= to run the file in one state."
            )


def prepare_flat_file(
    people: pd.DataFrame,
    *,
    year: int,
    state: Optional[Union[str, int]] = None,
) -> pd.DataFrame:
    """Check a flat file and write it in the form the pinned loader reads.

    Args:
        people: One row per person, with a group ID for each of the household,
            tax unit, SPM unit, family and marital unit, plus ``age``. Columns
            are named ``variable`` or ``variable__period``. ``person_id`` is
            optional. The run ignores columns that name no variable, and logs
            them.
        year: The year the file describes. A column without a period holds that
            year's value.
        state: A postal code or FIPS code to run every household in. It applies
            to every year the file holds, and clears stored state labels and all
            geography finer than a state. Leave it unset to keep the file's own
            ``state_fips``, which then has to agree with those columns.

    Returns:
        A new frame, leaving ``people`` as it was.
    """
    from policyengine_us.system import system

    if people.empty:
        raise ValueError("The file has no rows.")
    frame = _with_periods(people, year)
    frame = _without_unknown_columns(frame, system.variables)
    if _value_at(frame, "age", year) is None:
        raise ValueError(
            f"The file has no age for {year}, so everyone would run as a 40-year-old."
        )
    frame = _with_person_level_ids(frame, year)
    frame = _with_text_counties(frame)
    if state is not None:
        return _in_state(frame, _state_fips(state), year)
    _require_coherent_geography(frame, year)
    return frame


def flat_file_microsimulation(
    people: pd.DataFrame,
    *,
    year: int,
    state: Optional[Union[str, int]] = None,
    spm: Optional[SPMSelection] = None,
    **kwargs,
):
    """Build a bundled ``Microsimulation`` over a researcher's own flat file.

    A file moved to a ``state`` has no county, so county-keyed rules use the
    first county in that state, and SPM thresholds need
    ``spm={"geography_kind": "national"}``.

    Args:
        people: The flat file, as ``prepare_flat_file`` describes.
        year: The year the file describes.
        state: The state to run every household in, or ``None`` for the file's
            own ``state_fips``.
        spm: The SPM selection, which defaults to the bundle's.
        **kwargs: Passed on to ``Microsimulation``, for example ``reform``.

    Returns:
        A ``Microsimulation`` carrying this release's ``policyengine_bundle``.
    """
    from policyengine_core.data import Dataset
    from policyengine_us import Microsimulation

    if "dataset" in kwargs:
        raise ValueError("flat_file_microsimulation builds its dataset from `people`.")

    prepared = prepare_flat_file(people, year=year, state=state)
    microsim = Microsimulation(
        dataset=Dataset.from_dataframe(prepared, year),
        spm=resolve_spm_selection(spm),
        **kwargs,
    )
    microsim.policyengine_bundle = dict(us_latest.release_bundle)
    microsim.policyengine_bundle.update(
        build_runtime_dataset_provenance(
            "flat_file",
            "flat_file",
            None,
            logical_name="flat_file",
        )
    )
    microsim.policyengine_bundle["spm"] = dict(microsim.spm_config)
    return microsim
