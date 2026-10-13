"""Unit checks for the temporary ACS-local SPM compatibility (#597, #598).

Synthetic tables only: no country model or data download. The country-model
behaviour is covered in ``test_us_acs_local_spm_compatibility_integration``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from policyengine.tax_benefit_models.us import datasets as us_datasets
from policyengine.tax_benefit_models.us.spm_independence_role import (
    INDEPENDENCE_ROLE,
    independence_roles,
    roles_for_people,
)
from policyengine.tax_benefit_models.us.spm_measurement_scope import (
    ACS_LOCAL_SOURCE_SHA256,
    OUTSIDE_SPM_MEASUREMENT,
    SCOPE_RECORD_KEY,
    SCOPE_RULE,
    SPMMeasurementScope,
    applies_to_source,
    build_scope,
    check_scoped_spm_units,
    classify_spm_units,
    outside_by_spm_unit,
    read_scope_record,
    scope_from_metadata,
    write_scope_record,
)

ACS = "acs_2024_1yr"


def _tables():
    """One household, two group quarters and two non-ACS households.

    SPM units: 10 an ACS family with a minor reference person's sibling,
    20 an institutional group-quarters adult, 30 a noninstitutional
    group-quarters child, 40 an ASEC family, 50 a PUF teen living alone.
    """
    person = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5, 6, 7],
            "person_household_id": [1, 1, 2, 3, 4, 4, 5],
            "person_spm_unit_id": [10, 10, 20, 30, 40, 40, 50],
            "age": [17, 9, 45, 16, 38, 6, 16],
            "person_support_channel": [
                ACS,
                ACS,
                ACS,
                ACS,
                "asec",
                "asec",
                "puf_tax_detail",
            ],
            "RELSHIPP": [20.0, 25.0, 37.0, 38.0, np.nan, np.nan, np.nan],
            "is_household_head": [True, False, False, False, True, False, False],
        }
    )
    household = pd.DataFrame(
        {
            "household_id": [1, 2, 3, 4, 5],
            "TYPEHUGQ": [1.0, 2.0, 3.0, np.nan, np.nan],
        }
    )
    return person, household


def test_acs_group_quarters_units_are_outside_and_everyone_else_measured():
    person, household = _tables()
    outside = classify_spm_units(person, household)
    assert outside.to_dict() == {10: False, 20: True, 30: True, 40: False, 50: False}


def test_classification_never_reads_age():
    person, household = _tables()
    person["age"] = person["age"][::-1].to_numpy()
    assert (
        classify_spm_units(person, household).to_dict()
        == classify_spm_units(*_tables()).to_dict()
    )


@pytest.mark.parametrize(
    "change, message",
    [
        (
            lambda person, household: person.loc.__setitem__(
                (0, "person_support_channel"), "acs_2023"
            ),
            "no rule for source channels",
        ),
        (
            lambda person, household: person.loc.__setitem__(
                (0, "person_support_channel"), None
            ),
            "no rule for source channels",
        ),
        (
            lambda person, household: person.loc.__setitem__((2, "RELSHIPP"), np.nan),
            "cannot classify 1 people",
        ),
        (
            lambda person, household: person.loc.__setitem__((2, "RELSHIPP"), 38.0),
            "cannot classify 1 people",
        ),
        (
            lambda person, household: person.loc.__setitem__((0, "RELSHIPP"), 37.0),
            "cannot classify 1 people",
        ),
        (
            lambda person, household: household.loc.__setitem__(
                (0, "TYPEHUGQ"), np.nan
            ),
            "cannot classify 2 people",
        ),
        (
            lambda person, household: household.loc.__setitem__((3, "TYPEHUGQ"), 1.0),
            "cannot classify 2 people",
        ),
        (
            lambda person, household: person.loc.__setitem__((4, "RELSHIPP"), 20.0),
            "cannot classify 1 people",
        ),
        (
            lambda person, household: person.loc.__setitem__(
                (2, "person_spm_unit_id"), 10
            ),
            "mixing group-quarters",
        ),
        (
            lambda person, household: person.loc.__setitem__(
                (0, "person_household_id"), 99
            ),
            "cannot classify|unknown households",
        ),
        (
            lambda person, household: person.drop(columns=["RELSHIPP"], inplace=True),
            "needs person 'RELSHIPP'",
        ),
        (
            lambda person, household: household.drop(
                columns=["TYPEHUGQ"], inplace=True
            ),
            "needs household 'TYPEHUGQ'",
        ),
    ],
)
def test_unrecognised_or_inconsistent_evidence_raises(change, message):
    person, household = _tables()
    change(person, household)
    with pytest.raises(ValueError, match=message):
        classify_spm_units(person, household)


def test_rule_applies_only_to_the_certified_source():
    assert applies_to_source(ACS_LOCAL_SOURCE_SHA256)
    assert not applies_to_source(None)
    assert not applies_to_source("0" * 64)


def _scope(**overrides):
    values = dict(
        source_sha256=ACS_LOCAL_SOURCE_SHA256,
        outside=pd.Series([True, False, False]),
        independence_list_sha256="a" * 64,
        independence_list_people=2,
    )
    values.update(overrides)
    return build_scope(**values)


def test_scope_record_round_trips_through_metadata_and_h5(tmp_path):
    scope = _scope()
    assert scope.rule == SCOPE_RULE
    assert (scope.outside_spm_units, scope.measured_spm_units) == (1, 2)
    assert scope_from_metadata({SCOPE_RECORD_KEY: scope.model_dump()}) == scope
    assert scope_from_metadata({}) is None

    path = tmp_path / "file.h5"
    pd.DataFrame({"x": [1]}).to_hdf(path, key="person")
    assert read_scope_record(path) is None
    write_scope_record(path, scope)
    write_scope_record(path, scope)
    assert read_scope_record(path) == scope
    assert read_scope_record(tmp_path / "missing.h5") is None


def test_scope_record_rejects_unknown_fields_and_rules():
    record = _scope().model_dump()
    with pytest.raises(ValueError):
        SPMMeasurementScope.model_validate({**record, "extra": 1})
    with pytest.raises(ValueError):
        SPMMeasurementScope.model_validate({**record, "rule": "other"})


def test_alignment_refuses_unclassified_units():
    outside = pd.Series({10: False, 20: True})
    assert outside_by_spm_unit([20, 10], outside).tolist() == [True, False]
    with pytest.raises(ValueError, match="no classification for 1 SPM units"):
        outside_by_spm_unit([10, 99], outside)


@pytest.mark.parametrize(
    "column, message",
    [
        (None, "stores no"),
        ([True, None], "complete and boolean"),
        ([1, 0], "complete and boolean"),
    ],
)
def test_scoped_dataset_needs_a_complete_boolean_column(column, message):
    table = pd.DataFrame({"spm_unit_id": [1, 2]})
    if column is not None:
        table[OUTSIDE_SPM_MEASUREMENT] = column
    with pytest.raises(ValueError, match=message):
        check_scoped_spm_units(table, _scope())


# --- Independence role (#598) -------------------------------------------


def _write_list(path, rows):
    pd.DataFrame(
        rows, columns=["person_id", "person_spm_unit_id", "is_spm_independence_role"]
    ).to_csv(path, index=False)
    return path


def _list_rows():
    return [(5, 40, True), (6, 40, False), (7, 50, True)]


def test_non_acs_people_take_the_list_and_acs_people_the_model_fallback(tmp_path):
    person, _ = _tables()
    roles = independence_roles(person, _write_list(tmp_path / "l.csv", _list_rows()))
    # ACS: household head only (no stored spouse), as the model computes.
    # ASEC/PUF: the certified list, including the PUF teen living alone.
    assert roles.to_dict() == {
        1: True,
        2: False,
        3: False,
        4: False,
        5: True,
        6: False,
        7: True,
    }
    assert roles_for_people([7, 1], roles).tolist() == [True, True]
    with pytest.raises(ValueError, match="no value for 1 people"):
        roles_for_people([1, 99], roles)


def test_a_stored_spouse_counts_for_acs_people(tmp_path):
    person, _ = _tables()
    person["is_household_spouse"] = [False, False, True, False, False, False, False]
    roles = independence_roles(person, _write_list(tmp_path / "l.csv", _list_rows()))
    assert roles[3]


@pytest.mark.parametrize(
    "rows, message",
    [
        (_list_rows()[:2], "1 missing, 0 not in the source"),
        ([*_list_rows(), (8, 50, False)], "0 missing, 1 not in the source"),
        ([*_list_rows(), (1, 10, False)], "0 missing, 1 not in the source"),
        ([(5, 40, True), (6, 40, False), (7, 40, True)], "different SPM unit"),
        ([*_list_rows(), (7, 50, True)], "repeats person IDs"),
        ([(5, 40, True), (6, 40, "yes"), (7, 50, True)], "non-boolean"),
        ([(5, 40, True), (6, 40, None), (7, 50, True)], "non-boolean"),
    ],
)
def test_the_list_must_match_the_non_acs_people_exactly(tmp_path, rows, message):
    person, _ = _tables()
    with pytest.raises(ValueError, match=message):
        independence_roles(person, _write_list(tmp_path / "l.csv", rows))


def test_a_source_that_stores_the_role_retires_the_patch(tmp_path):
    person, _ = _tables()
    person[INDEPENDENCE_ROLE] = False
    with pytest.raises(ValueError, match="delete the temporary"):
        independence_roles(person, _write_list(tmp_path / "l.csv", _list_rows()))


def test_unexpected_list_columns_are_refused(tmp_path):
    person, _ = _tables()
    path = tmp_path / "l.csv"
    pd.DataFrame({"person_id": [5], "role": [True]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Unexpected SPM independence list"):
        independence_roles(person, path)


# --- Year-file staleness -------------------------------------------------


def test_only_acs_local_year_files_must_record_the_scope(tmp_path):
    path = tmp_path / "year.h5"
    pd.DataFrame({"x": [1]}).to_hdf(path, key="person")
    assert us_datasets._managed_source_sha256("populace_us_2024_acs_local") == (
        ACS_LOCAL_SOURCE_SHA256
    )
    assert us_datasets._year_file_records_scope(path, "populace_us_2024")
    assert us_datasets._year_file_records_scope(path, "hf://other/repo/file.h5")
    assert not us_datasets._year_file_records_scope(path, "populace_us_2024_acs_local")

    write_scope_record(path, _scope(source_sha256="0" * 64))
    assert not us_datasets._year_file_records_scope(path, "populace_us_2024_acs_local")
    write_scope_record(path, _scope())
    assert us_datasets._year_file_records_scope(path, "populace_us_2024_acs_local")
