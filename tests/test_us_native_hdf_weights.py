"""Native pandas HDF weights are projected through IDs without editing the H5."""

import hashlib

import numpy as np
import pandas as pd
import pytest

from policyengine.tax_benefit_models.us.datasets import PolicyEngineUSDataset


@pytest.fixture
def native_frames():
    """Small BuildP-shaped source with only calibrated household weights.

    ID order and pandas indexes intentionally differ across every table. Three
    people share one SPM unit; its weight must remain one household weight.
    """
    return {
        "person": pd.DataFrame(
            {
                "person_id": [101, 20, 888, 42, 5],
                "person_household_id": [12, 900, 12, 900, 12],
                "person_tax_unit_id": [21, 700, 21, 9, 21],
                "person_spm_unit_id": [6, 8800, 6, 8800, 6],
                "person_family_id": [8, 99, 8, 99, 8],
                "person_marital_unit_id": [3, 67, 10, 25, 3],
                "age": np.array([16, 40, 8, 33, 3], dtype=np.int16),
                "is_spm_independent_minor_role": [True, True, False, True, False],
                "employment_income": [0.0, 24_000.0, 0.0, 30_000.0, 0.0],
            },
            index=pd.Index([19, -4, 60, 3, 100], name="source_row"),
        ),
        "household": pd.DataFrame(
            {
                "household_id": [900, 12],
                "household_weight": [3.25, 8.5],
                "county_fips": np.array(["06037", "48201"], dtype=object),
            },
            index=pd.Index([44, -10], name="source_row"),
        ),
        "tax_unit": pd.DataFrame({"tax_unit_id": [700, 9, 21]}, index=[50, -2, 19]),
        "spm_unit": pd.DataFrame(
            {"spm_unit_id": [6, 8800], "source_audit_amount": [10.0, 100.0]},
            index=[81, 3],
        ),
        "family": pd.DataFrame({"family_id": [99, 8]}, index=[0, -80]),
        "marital_unit": pd.DataFrame(
            {"marital_unit_id": [25, 3, 67, 10]}, index=[7, 200, -12, 31]
        ),
    }


EXPECTED_WEIGHTS = {
    "person": [8.5, 3.25, 8.5, 3.25, 8.5],
    "household": [3.25, 8.5],
    "tax_unit": [3.25, 3.25, 8.5],
    "spm_unit": [8.5, 3.25],
    "family": [3.25, 8.5],
    "marital_unit": [3.25, 8.5, 3.25, 8.5],
}


def write_native_hdf(tmp_path, frames, format):
    path = tmp_path / f"native-{format}.h5"
    with pd.HDFStore(path, mode="w") as store:
        for entity, frame in frames.items():
            store.put(entity, frame, format=format)
    return path


def load_native_hdf(path):
    return PolicyEngineUSDataset(
        name="Synthetic native household-weight fixture",
        description="Uncertified five-person loader regression",
        filepath=str(path),
        year=2024,
    )


@pytest.mark.parametrize("format", ["fixed", "table"])
@pytest.mark.parametrize("link_style", ["native", "plain"])
def test_native_hdf_derives_missing_weights_by_ids_without_changing_source(
    tmp_path, native_frames, format, link_style
):
    if link_style == "plain":
        native_frames["person"] = native_frames["person"].rename(
            columns={
                f"person_{entity}_id": f"{entity}_id"
                for entity in native_frames
                if entity != "person"
            }
        )
    path = write_native_hdf(tmp_path, native_frames, format)
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    dataset = load_native_hdf(path)

    for entity, original in native_frames.items():
        loaded = getattr(dataset.data, entity)
        # Existing arrays, dtypes, county, primitive roles and native indexes
        # survive unchanged; derived weight columns exist only in memory.
        pd.testing.assert_frame_equal(pd.DataFrame(loaded)[original.columns], original)
        expected = pd.Series(
            EXPECTED_WEIGHTS[entity], index=original.index, name=f"{entity}_weight"
        )
        pd.testing.assert_series_equal(
            pd.DataFrame(loaded)[f"{entity}_weight"], expected
        )
        pd.testing.assert_series_equal(loaded.weights, expected, check_names=False)

    assert dataset.data.person.employment_income.sum() == 175_500.0
    assert dataset.data.spm_unit.source_audit_amount.sum() == 410.0
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    with pd.HDFStore(path, mode="r") as store:
        for entity, original in native_frames.items():
            pd.testing.assert_frame_equal(store[entity], original)


@pytest.mark.parametrize("format", ["fixed", "table"])
def test_existing_person_and_entity_weights_are_preserved(
    tmp_path, native_frames, format
):
    # Deliberately distinct supplied weights catch both overwriting and using
    # person weights as the source for missing group weights.
    native_frames["person"]["person_weight"] = [11.0, 12.0, 13.0, 14.0, 15.0]
    native_frames["tax_unit"]["tax_unit_weight"] = [23.0, 24.0, 25.0]
    native_frames["family"]["family_weight"] = [31.0, 32.0]
    path = write_native_hdf(tmp_path, native_frames, format)
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    dataset = load_native_hdf(path)

    for entity, original in native_frames.items():
        loaded = getattr(dataset.data, entity)
        pd.testing.assert_frame_equal(pd.DataFrame(loaded)[original.columns], original)
        expected = (
            original[f"{entity}_weight"].tolist()
            if f"{entity}_weight" in original
            else EXPECTED_WEIGHTS[entity]
        )
        assert loaded.weights.tolist() == expected
        assert pd.DataFrame(loaded)[f"{entity}_weight"].tolist() == expected
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_native_person_links_take_precedence_over_plain_aliases(
    tmp_path, native_frames
):
    for entity, frame in native_frames.items():
        if entity != "person":
            native_frames["person"][f"{entity}_id"] = frame[f"{entity}_id"].iloc[0]
    path = write_native_hdf(tmp_path, native_frames, "table")
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    dataset = load_native_hdf(path)

    for entity, original in native_frames.items():
        loaded = getattr(dataset.data, entity)
        pd.testing.assert_frame_equal(pd.DataFrame(loaded)[original.columns], original)
        assert loaded.weights.tolist() == EXPECTED_WEIGHTS[entity]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_empty_native_entity_tables_keep_indexes_and_source_weight_dtype(
    tmp_path, native_frames
):
    frames = {entity: frame.iloc[:0].copy() for entity, frame in native_frames.items()}
    path = write_native_hdf(tmp_path, frames, "fixed")
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    dataset = load_native_hdf(path)

    for entity, original in frames.items():
        loaded = pd.DataFrame(getattr(dataset.data, entity))
        pd.testing.assert_frame_equal(loaded[original.columns], original)
        assert loaded[f"{entity}_weight"].empty
        assert (
            loaded[f"{entity}_weight"].dtype
            == frames["household"]["household_weight"].dtype
        )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(
    "problem",
    [
        "missing_person_household_link",
        "unknown_household_id",
        "duplicate_household_id",
        "orphan_spm_unit",
        "spm_unit_spans_households",
    ],
)
def test_missing_or_ambiguous_native_links_raise_without_mutating_hdf(
    tmp_path, native_frames, problem
):
    if problem == "missing_person_household_link":
        native_frames["person"] = native_frames["person"].drop(
            columns="person_household_id"
        )
    elif problem == "unknown_household_id":
        native_frames["person"].loc[19, "person_household_id"] = 404
    elif problem == "duplicate_household_id":
        native_frames["household"].loc[-10, "household_id"] = 900
    elif problem == "orphan_spm_unit":
        native_frames["spm_unit"].loc[81, "spm_unit_id"] = 404
    elif problem == "spm_unit_spans_households":
        native_frames["person"].loc[-4, "person_spm_unit_id"] = 6
    path = write_native_hdf(tmp_path, native_frames, "table")
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="weight|household|spm_unit"):
        load_native_hdf(path)

    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("format", ["fixed", "table"])
@pytest.mark.parametrize("entity", ["tax_unit", "spm_unit", "family", "marital_unit"])
@pytest.mark.parametrize("problem", ["missing", "duplicate"])
def test_invalid_group_ids_rejected_before_weight_mapping(
    tmp_path, native_frames, format, entity, problem
):
    entity_id = f"{entity}_id"
    frame = native_frames[entity]
    if problem == "missing":
        # Matching null membership used to map successfully through pandas.
        old_id = frame[entity_id].iloc[0]
        frame.loc[frame.index[0], entity_id] = np.nan
        link = f"person_{entity_id}"
        person = native_frames["person"]
        person.loc[person[link] == old_id, link] = np.nan
    else:
        # A repeated complete row used to duplicate its household weight and
        # silently increase weighted totals (SPM audit total 410 -> 495).
        native_frames[entity] = pd.concat([frame, frame.iloc[[0]]])
    path = write_native_hdf(tmp_path, native_frames, format)
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match=f"unique nonmissing {entity_id}"):
        load_native_hdf(path)

    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
