"""Tests for UK dataset person/benunit weight derivation.

Published UK microdata carries only `household_weight`. Person and benunit
weights are derived from it, both when a dataset is built through
`create_datasets` and when a caller supplies a filepath directly.
"""

import pandas as pd
import pytest

from policyengine.tax_benefit_models.uk.datasets import (
    PolicyEngineUKDataset,
    derive_benunit_weight,
    derive_person_weight,
)


@pytest.fixture
def frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Minimal UK-shaped frames carrying only `household_weight`."""
    household = pd.DataFrame(
        {
            "household_id": [1, 2],
            "household_weight": [10.0, 20.0],
        }
    )
    person = pd.DataFrame(
        {
            "person_id": [1, 2, 3],
            "person_benunit_id": [11, 11, 12],
            "person_household_id": [1, 1, 2],
        }
    )
    benunit = pd.DataFrame({"benunit_id": [11, 12]})
    return person, benunit, household


def test_derive_person_weight_when_missing(frames):
    person, _, household = frames

    result = derive_person_weight(person, household)

    assert result["person_weight"].tolist() == [10.0, 10.0, 20.0]
    assert "household_id" not in result.columns


def test_derive_benunit_weight_when_missing(frames):
    person, benunit, household = frames

    result = derive_benunit_weight(benunit, person, household)

    assert result["benunit_weight"].tolist() == [10.0, 20.0]
    assert "person_household_id" not in result.columns


def test_derive_person_weight_is_a_no_op_when_present(frames):
    person, _, household = frames
    person = person.assign(person_weight=[1.0, 2.0, 3.0])

    result = derive_person_weight(person, household)

    assert result is person
    assert result["person_weight"].tolist() == [1.0, 2.0, 3.0]


def test_derive_benunit_weight_is_a_no_op_when_present(frames):
    person, benunit, household = frames
    benunit = benunit.assign(benunit_weight=[5.0, 6.0])

    result = derive_benunit_weight(benunit, person, household)

    assert result is benunit
    assert result["benunit_weight"].tolist() == [5.0, 6.0]


def test_derive_person_weight_reports_missing_join_column(frames):
    person, _, household = frames

    with pytest.raises(KeyError, match="person_household_id"):
        derive_person_weight(person.drop(columns=["person_household_id"]), household)


def test_derive_weights_report_missing_household_weight(frames):
    person, benunit, household = frames
    household = household.drop(columns=["household_weight"])

    with pytest.raises(KeyError, match="household_weight"):
        derive_person_weight(person, household)
    with pytest.raises(KeyError, match="household_weight"):
        derive_benunit_weight(benunit, person, household)


def test_load_derives_weights_for_a_directly_supplied_dataset(tmp_path, frames):
    """A dataset file with only `household_weight` loads without a KeyError.

    This is the regression: published UK datasets (e.g. an Enhanced FRS
    release) have no `person_weight` column, so constructing
    `PolicyEngineUKDataset(filepath=...)` used to raise `KeyError`.
    """
    person, benunit, household = frames
    filepath = tmp_path / "uk.h5"
    with pd.HDFStore(filepath, mode="w") as store:
        store.put("person", person, format="table")
        store.put("benunit", benunit, format="table")
        store.put("household", household, format="table")

    dataset = PolicyEngineUKDataset(
        name="uk",
        description="uk",
        filepath=str(filepath),
        year=2024,
    )

    assert dataset.data.person["person_weight"].tolist() == [10.0, 10.0, 20.0]
    assert dataset.data.benunit["benunit_weight"].tolist() == [10.0, 20.0]
    assert dataset.data.household["household_weight"].tolist() == [10.0, 20.0]


def test_load_preserves_existing_person_weights(tmp_path, frames):
    """A dataset carrying its own person-level weights is not overwritten."""
    person, benunit, household = frames
    person = person.assign(person_weight=[1.0, 2.0, 3.0])
    benunit = benunit.assign(benunit_weight=[5.0, 6.0])
    filepath = tmp_path / "uk.h5"
    with pd.HDFStore(filepath, mode="w") as store:
        store.put("person", person, format="table")
        store.put("benunit", benunit, format="table")
        store.put("household", household, format="table")

    dataset = PolicyEngineUKDataset(
        name="uk",
        description="uk",
        filepath=str(filepath),
        year=2024,
    )

    assert dataset.data.person["person_weight"].tolist() == [1.0, 2.0, 3.0]
    assert dataset.data.benunit["benunit_weight"].tolist() == [5.0, 6.0]


def test_derivation_matches_the_create_datasets_merge(frames):
    """The shared helpers reproduce the merge `create_datasets` used inline."""
    person, benunit, household = frames

    expected_person = person.merge(
        household[["household_id", "household_weight"]],
        left_on="person_household_id",
        right_on="household_id",
        how="left",
    )
    expected_person = expected_person.rename(
        columns={"household_weight": "person_weight"}
    ).drop(columns=["household_id"])

    benunit_household_map = expected_person[
        ["person_benunit_id", "person_household_id"]
    ].drop_duplicates()
    expected_benunit = benunit.merge(
        benunit_household_map,
        left_on="benunit_id",
        right_on="person_benunit_id",
        how="left",
    ).merge(
        household[["household_id", "household_weight"]],
        left_on="person_household_id",
        right_on="household_id",
        how="left",
    )
    expected_benunit = expected_benunit.rename(
        columns={"household_weight": "benunit_weight"}
    ).drop(
        columns=["person_benunit_id", "person_household_id", "household_id"],
        errors="ignore",
    )

    pd.testing.assert_frame_equal(
        derive_person_weight(person, household), expected_person
    )
    pd.testing.assert_frame_equal(
        derive_benunit_weight(benunit, person, household), expected_benunit
    )
