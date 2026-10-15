"""Unit checks for backward compatibility with legacy US SPM sources.

Covers PolicyEngine/policyengine.py#597 and #598 with synthetic tables only:
no country model and no data download. The country-model behaviour is in
``test_us_legacy_spm_integration`` and the model contract in
``test_us_legacy_spm_model_contract``.
"""

from __future__ import annotations

import json

import h5py
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from policyengine.provenance.manifest import get_release_manifest
from policyengine.tax_benefit_models.us import datasets as us_datasets
from policyengine.tax_benefit_models.us.legacy_inputs import _ABSENT
from policyengine.tax_benefit_models.us.legacy_spm import (
    ADAPTER_REVISION,
    LEGACY_SPM_SOURCES,
    RECORD_H5_DATASET,
    LegacySPMRecord,
    LegacySPMSource,
    expected_profile,
    legacy_spm_source,
    parse_record,
    read_record_value,
    record_problem,
    write_record,
    year_file_problem,
)
from policyengine.tax_benefit_models.us.legacy_spm.independence import (
    INDEPENDENCE_ROLE,
    independence_roles,
)
from policyengine.tax_benefit_models.us.legacy_spm.registry import (
    POPULACE_US_2024_ACS_LOCAL_BUILD_O,
)
from policyengine.tax_benefit_models.us.legacy_spm.universe import (
    classify_acs_household_population,
)

ACS = "acs_2024_1yr"
BUILD_O = POPULACE_US_2024_ACS_LOCAL_BUILD_O


def _tables():
    """One ACS household, two group quarters, and two non-ACS households.

    SPM units: 10 an ACS family whose reference person is 17, 20 an
    institutional group-quarters adult, 30 a noninstitutional group-quarters
    child, 40 an ASEC family, 50 a PUF teen living alone.
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
        {"household_id": [1, 2, 3, 4, 5], "TYPEHUGQ": [1.0, 2.0, 3.0, np.nan, np.nan]}
    )
    return person, household


# --- Registry -------------------------------------------------------------


def test_registry_keys_are_unique_and_match_the_bundle():
    hashes = [source.source_sha256 for source in LEGACY_SPM_SOURCES]
    assert len(hashes) == len(set(hashes))
    manifest = get_release_manifest("us")
    assert manifest.datasets["populace_us_2024_acs_local"].sha256 == (
        BUILD_O.source_sha256
    )
    pin = BUILD_O.independence_list
    assert pin is not None
    assert manifest.datasets[pin.bundle_dataset].sha256 == pin.sha256


def test_only_registered_sources_are_legacy():
    assert legacy_spm_source(BUILD_O.source_sha256) == BUILD_O
    assert legacy_spm_source(None) is None
    assert legacy_spm_source("0" * 64) is None
    default = get_release_manifest("us").datasets["populace_us_2024"]
    assert legacy_spm_source(default.sha256) is None


def test_registry_entries_are_validated():
    with pytest.raises(ValueError):
        LegacySPMSource(name="x", source_sha256="y", spm_universe_rule="other")
    with pytest.raises(ValueError):
        LegacySPMSource(name="x", source_sha256="y", unknown=True)


# --- Measurement scope (#597) ----------------------------------------------


def test_acs_group_quarters_are_outside_and_everyone_else_included():
    person, household = _tables()
    assert classify_acs_household_population(person, household).to_dict() == {
        10: "INCLUDED",
        20: "OUTSIDE",
        30: "OUTSIDE",
        40: "INCLUDED",
        50: "INCLUDED",
    }


def test_classification_never_reads_age():
    person, household = _tables()
    person["age"] = person["age"][::-1].to_numpy()
    reversed_ages = classify_acs_household_population(person, household)
    assert reversed_ages.to_dict() == (
        classify_acs_household_population(*_tables()).to_dict()
    )


def _set_person(row, column, value):
    def change(person, household):
        person.loc[row, column] = value

    return change


def _set_household(row, column, value):
    def change(person, household):
        household.loc[row, column] = value

    return change


def _drop(table_name, column):
    def change(person, household):
        table = person if table_name == "person" else household
        table.drop(columns=[column], inplace=True)

    return change


@pytest.mark.parametrize(
    "change, message",
    [
        (_set_person(0, "person_support_channel", "acs_2023"), "no rule for source"),
        (_set_person(0, "person_support_channel", None), "no rule for source"),
        (_set_person(2, "RELSHIPP", np.nan), "cannot classify 1 people"),
        (_set_person(2, "RELSHIPP", 38.0), "cannot classify 1 people"),
        (_set_person(0, "RELSHIPP", 37.0), "cannot classify 1 people"),
        (_set_household(0, "TYPEHUGQ", np.nan), "cannot classify 2 people"),
        (_set_household(3, "TYPEHUGQ", 1.0), "cannot classify 2 people"),
        (_set_person(4, "RELSHIPP", 20.0), "cannot classify 1 people"),
        (_set_person(2, "person_spm_unit_id", 10), "mixing group-quarters"),
        (_set_person(0, "person_household_id", 99), "unknown households"),
        (_drop("person", "RELSHIPP"), "needs person 'RELSHIPP'"),
        (_drop("household", "TYPEHUGQ"), "needs household 'TYPEHUGQ'"),
    ],
)
def test_unrecognised_or_inconsistent_evidence_raises(change, message):
    person, household = _tables()
    change(person, household)
    with pytest.raises(ValueError, match=message):
        classify_acs_household_population(person, household)


#: Per-person evidence: (channel, household TYPEHUGQ, RELSHIPP).
_EVIDENCE = st.sampled_from(
    [
        (ACS, 1.0, 20.0),
        (ACS, 1.0, 25.0),
        (ACS, 2.0, 37.0),
        (ACS, 3.0, 38.0),
        ("asec", np.nan, np.nan),
        ("puf_tax_detail", np.nan, np.nan),
        (ACS, 2.0, 38.0),
        (ACS, 1.0, 37.0),
        (ACS, np.nan, 20.0),
        (ACS, 1.0, np.nan),
        ("asec", 1.0, np.nan),
        ("other", np.nan, np.nan),
    ]
)


def _oracle_status(channel, record_type, relationship) -> str | None:
    """The rule for one person, stated independently of the classifier."""
    if channel == ACS:
        if record_type == 1 and relationship == relationship:
            return None if relationship in (37, 38) else "INCLUDED"
        if (record_type, relationship) in {(2, 37), (3, 38)}:
            return "OUTSIDE"
        return None
    if channel in ("asec", "puf_tax_detail"):
        if record_type != record_type and relationship != relationship:
            return "INCLUDED"
    return None


@settings(max_examples=300, deadline=None)
@given(
    units=st.lists(st.lists(_EVIDENCE, min_size=1, max_size=3), min_size=1, max_size=6),
    ages=st.lists(st.integers(0, 90), min_size=18, max_size=18),
)
def test_classification_agrees_with_the_rule_for_any_population(units, ages):
    """Each SPM unit is its own household; ages are arbitrary and unused."""
    rows, households = [], []
    expected: dict[int, str] = {}
    valid = True
    for unit_index, members in enumerate(units):
        household_id = unit_index + 1
        record_type = members[0][1]
        households.append({"household_id": household_id, "TYPEHUGQ": record_type})
        statuses = set()
        for channel, _, relationship in members:
            rows.append(
                {
                    "person_id": len(rows) + 1,
                    "person_household_id": household_id,
                    "person_spm_unit_id": household_id * 10,
                    "age": ages[len(rows) % len(ages)],
                    "person_support_channel": channel,
                    "RELSHIPP": relationship,
                }
            )
            statuses.add(_oracle_status(channel, record_type, relationship))
        if None in statuses or len(statuses) > 1:
            valid = False
        else:
            expected[household_id * 10] = statuses.pop()
    person, household = pd.DataFrame(rows), pd.DataFrame(households)
    if valid:
        assert classify_acs_household_population(person, household).to_dict() == (
            expected
        )
    else:
        with pytest.raises(ValueError):
            classify_acs_household_population(person, household)


# --- Independence role (#598) ------------------------------------------------


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
    assert roles.to_dict() == {
        1: True,
        2: False,
        3: False,
        4: False,
        5: True,
        6: False,
        7: True,
    }


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


def test_a_source_that_stores_the_role_is_not_legacy_for_it(tmp_path):
    person, _ = _tables()
    person[INDEPENDENCE_ROLE] = False
    with pytest.raises(ValueError, match="not a legacy source"):
        independence_roles(person, _write_list(tmp_path / "l.csv", _list_rows()))


def test_unexpected_list_columns_are_refused(tmp_path):
    person, _ = _tables()
    path = tmp_path / "l.csv"
    pd.DataFrame({"person_id": [5], "role": [True]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Unexpected SPM independence list"):
        independence_roles(person, path)


# --- Records: total and exact ---------------------------------------------


def _record(**source_changes) -> LegacySPMRecord:
    source = BUILD_O.model_copy(update=source_changes)
    return LegacySPMRecord(
        profile=expected_profile(source),
        outside_spm_units=2,
        included_spm_units=3,
        independence_list_people=3,
    )


def _empty_h5(path):
    pd.DataFrame({"x": [1]}).to_hdf(path, key="person")
    return path


def test_a_record_round_trips_through_h5(tmp_path):
    path = _empty_h5(tmp_path / "file.h5")
    assert read_record_value(path) is _ABSENT
    write_record(path, _record())
    write_record(path, _record())
    assert parse_record(read_record_value(path)) == _record()
    assert year_file_problem(path, expected_profile(BUILD_O)) is None


def test_the_profile_must_match_exactly():
    expected = expected_profile(BUILD_O)
    assert record_problem(_record(), expected) is None
    other_list = BUILD_O.independence_list.model_copy(update={"sha256": "0" * 64})
    for changed in (
        _record(independence_list=other_list),
        _record(independence_list=None),
        _record(spm_universe_rule=None),
        _record(source_sha256="0" * 64),
    ):
        assert "derived under profile" in record_problem(changed, expected)
    newer = _record().model_copy(
        update={
            "profile": expected.model_copy(
                update={"adapter_revision": ADAPTER_REVISION + 1}
            )
        }
    )
    assert "derived under profile" in record_problem(newer, expected)


def test_a_records_model_mode_is_provenance_not_profile():
    with_mode = _record().model_copy(update={"model_mode": "override"})
    assert record_problem(with_mode, expected_profile(BUILD_O)) is None


def test_records_are_required_exactly_when_the_source_needs_them():
    expected = expected_profile(BUILD_O)
    assert record_problem(_ABSENT, None) is None
    assert "no record" in record_problem(_ABSENT, expected)
    assert "does not need" in record_problem(_record(), None)


#: Arbitrary JSON values a record node might hold.
_JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(),
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(st.text(max_size=12), children, max_size=4)
    ),
    max_leaves=12,
)


@settings(max_examples=200, deadline=None)
@given(
    stored=st.one_of(
        _JSON,
        st.builds(
            lambda key, value: {**_record().model_dump(mode="json"), key: value},
            st.sampled_from(["schema_version", "profile", "extra", "model_mode"]),
            _JSON,
        ),
        st.just(_record().model_dump(mode="json")),
    )
)
def test_the_check_is_total_and_accepts_only_the_expected_profile(
    stored, tmp_path_factory
):
    path = _empty_h5(tmp_path_factory.mktemp("record") / "file.h5")
    with h5py.File(path, "a") as file:
        file.create_dataset(
            RECORD_H5_DATASET,
            data=json.dumps(stored),
            dtype=h5py.string_dtype("utf-8"),
        )
    expected = expected_profile(BUILD_O)
    problem = year_file_problem(path, expected)
    record = parse_record(stored)
    assert (problem is None) == (record is not None and record.profile == expected)


@pytest.mark.parametrize(
    "stored",
    [
        np.void(b"\xff\xfe not utf-8"),
        "{not json",
        "[" * 100_000 + "]" * 100_000,
        np.arange(3),
    ],
    # Explicit IDs: pytest would otherwise use the 200,000-character string as
    # its test ID, which exceeds Windows' environment-variable limit for
    # PYTEST_CURRENT_TEST and floods verbose CI logs.
    ids=["bytes_not_utf8", "text_not_json", "json_nested_too_deeply", "number_array"],
)
def test_unreadable_records_are_out_of_date_not_errors(tmp_path, stored):
    path = _empty_h5(tmp_path / "file.h5")
    with h5py.File(path, "a") as file:
        if isinstance(stored, str):
            file.create_dataset(
                RECORD_H5_DATASET, data=stored, dtype=h5py.string_dtype("utf-8")
            )
        else:
            file.create_dataset(RECORD_H5_DATASET, data=stored)
    assert "unreadable" in year_file_problem(path, expected_profile(BUILD_O))


def test_a_file_that_is_not_hdf5_is_out_of_date(tmp_path):
    path = tmp_path / "file.h5"
    path.write_bytes(b"not hdf5")
    assert year_file_problem(path, expected_profile(BUILD_O)) is not None


# --- Year-file decisions ---------------------------------------------------


def test_only_legacy_year_files_must_record_declarations(tmp_path):
    path = _empty_h5(tmp_path / "year.h5")
    acs_local = us_datasets._expected_legacy_spm_profile("populace_us_2024_acs_local")
    assert acs_local == expected_profile(BUILD_O)
    assert us_datasets._expected_legacy_spm_profile("populace_us_2024") is None
    assert us_datasets._expected_legacy_spm_profile("hf://other/repo/x.h5") is None
    assert year_file_problem(path, acs_local) is not None
    write_record(path, _record())
    assert year_file_problem(path, acs_local) is None
    assert year_file_problem(path, None) is not None


def test_a_managed_dataset_is_recognised_by_its_uri_too():
    from policyengine.provenance.manifest import resolve_dataset_reference

    uri = resolve_dataset_reference("us", "populace_us_2024_acs_local")
    assert uri.startswith("hf://")
    assert us_datasets._expected_legacy_spm_profile(uri) == expected_profile(BUILD_O)
    default_uri = resolve_dataset_reference("us", "populace_us_2024")
    assert us_datasets._expected_legacy_spm_profile(default_uri) is None


# --- Year-file frame guards -------------------------------------------------


def _declared_frames():
    from policyengine.tax_benefit_models.us.legacy_spm import UNIVERSE_VARIABLE

    person = pd.DataFrame({"person_id": [1, 2], INDEPENDENCE_ROLE: [True, False]})
    spm_unit = pd.DataFrame(
        {"spm_unit_id": [1, 2], UNIVERSE_VARIABLE: ["INCLUDED", "OUTSIDE"]}
    )
    return person, spm_unit


def test_complete_declarations_pass_the_frame_check():
    from policyengine.tax_benefit_models.us.legacy_spm import check_year_file_frames

    person, spm_unit = _declared_frames()
    check_year_file_frames(person, spm_unit, _record())
    spm_unit["spm_unit_spm_universe_status"] = [b"INCLUDED", b"OUTSIDE"]
    check_year_file_frames(person, spm_unit, _record())


def _drop_column(table, column):
    def change(person, spm_unit):
        (person if table == "person" else spm_unit).drop(columns=[column], inplace=True)

    return change


def _set_column(table, column, values):
    def change(person, spm_unit):
        (person if table == "person" else spm_unit)[column] = values

    return change


@pytest.mark.parametrize(
    "change, message",
    [
        (
            _drop_column("spm_unit", "spm_unit_spm_universe_status"),
            "stores no 'spm_unit_spm_universe_status'",
        ),
        (
            _set_column(
                "spm_unit", "spm_unit_spm_universe_status", ["INCLUDED", "UNRESOLVED"]
            ),
            "must declare every SPM unit",
        ),
        (
            _set_column("spm_unit", "spm_unit_spm_universe_status", ["INCLUDED", None]),
            "must declare every SPM unit",
        ),
        (
            _drop_column("person", INDEPENDENCE_ROLE),
            "stores no 'is_spm_independent_minor_role'",
        ),
        (
            _set_column("person", INDEPENDENCE_ROLE, [True, None]),
            "must be complete and boolean",
        ),
        (
            _set_column("person", INDEPENDENCE_ROLE, [1, 0]),
            "must be complete and boolean",
        ),
    ],
)
def test_incomplete_or_invalid_declarations_fail_the_frame_check(change, message):
    from policyengine.tax_benefit_models.us.legacy_spm import check_year_file_frames

    person, spm_unit = _declared_frames()
    change(person, spm_unit)
    with pytest.raises(ValueError, match=message):
        check_year_file_frames(person, spm_unit, _record())


def test_only_the_declarations_a_source_needs_are_required():
    from policyengine.tax_benefit_models.us.legacy_spm import check_year_file_frames

    person, spm_unit = _declared_frames()
    person.drop(columns=[INDEPENDENCE_ROLE], inplace=True)
    check_year_file_frames(person, spm_unit, _record(independence_list=None))
    spm_unit.drop(columns=["spm_unit_spm_universe_status"], inplace=True)
    check_year_file_frames(
        person, spm_unit, _record(independence_list=None, spm_universe_rule=None)
    )
