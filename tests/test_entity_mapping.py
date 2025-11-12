import pandas as pd
import pytest
from microdf import MicroDataFrame
from policyengine.tax_benefit_models.uk import UKYearData


def test_map_same_entity():
    """Test mapping from an entity to itself returns the same data."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "age": [30, 25, 40],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame({"benunit_id": [1, 2], "benunit_weight": [1.0, 1.0]}),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame({"household_id": [1, 2], "household_weight": [1.0, 1.0]}),
        weights="household_weight",
    )

    data = UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    )

    # Test person -> person
    result = data.map_to_entity("person", "person")
    assert isinstance(result, MicroDataFrame)
    assert len(result) == 3
    assert list(result["person_id"]) == [1, 2, 3]

    # Test benunit -> benunit
    result = data.map_to_entity("benunit", "benunit")
    assert isinstance(result, MicroDataFrame)
    assert len(result) == 2
    assert list(result["benunit_id"]) == [1, 2]

    # Test household -> household
    result = data.map_to_entity("household", "household")
    assert isinstance(result, MicroDataFrame)
    assert len(result) == 2
    assert list(result["household_id"]) == [1, 2]


def test_map_person_to_benunit():
    """Test mapping person-level data to benunit level."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "age": [30, 25, 40],
                "income": [50000, 30000, 60000],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame({"benunit_id": [1, 2], "benunit_weight": [1.0, 1.0]}),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame({"household_id": [1, 2], "household_weight": [1.0, 1.0]}),
        weights="household_weight",
    )

    data = UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    )

    result = data.map_to_entity("person", "benunit")

    # Should return a MicroDataFrame
    assert isinstance(result, MicroDataFrame)
    # Should have rows for each person
    assert len(result) == 3
    # Should have benunit data merged in
    assert "benunit_id" in result.columns
    assert "person_id" in result.columns


def test_map_person_to_household():
    """Test mapping person-level data to household level."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "age": [30, 25, 40],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame({"benunit_id": [1, 2], "benunit_weight": [1.0, 1.0]}),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "rent": [1000, 800],
                "household_weight": [1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    data = UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    )

    result = data.map_to_entity("person", "household")

    # Should have rows for each person
    assert len(result) == 3
    # Should have household data merged in
    assert "household_id" in result.columns
    assert "person_id" in result.columns
    assert "rent" in result.columns


def test_map_benunit_to_person():
    """Test mapping benunit-level data to person level."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2],
                "total_benefit": [1000, 500],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame({"household_id": [1, 2], "household_weight": [1.0, 1.0]}),
        weights="household_weight",
    )

    data = UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    )

    result = data.map_to_entity("benunit", "person")

    # Should have rows for each person
    assert len(result) == 3
    # Should have benunit data merged in
    assert "benunit_id" in result.columns
    assert "person_id" in result.columns
    assert "total_benefit" in result.columns


def test_map_benunit_to_household():
    """Test mapping benunit-level data to household level."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "benunit_id": [1, 1, 2, 2],
                "household_id": [1, 1, 2, 2],
                "person_weight": [1.0, 1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2],
                "total_benefit": [1000, 500],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame({"household_id": [1, 2], "household_weight": [1.0, 1.0]}),
        weights="household_weight",
    )

    data = UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    )

    result = data.map_to_entity("benunit", "household")

    # Should have benunit and household data
    assert "benunit_id" in result.columns
    assert "household_id" in result.columns
    assert "total_benefit" in result.columns


def test_map_household_to_person():
    """Test mapping household-level data to person level."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame({"benunit_id": [1, 2], "benunit_weight": [1.0, 1.0]}),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "rent": [1000, 800],
                "household_weight": [1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    data = UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    )

    result = data.map_to_entity("household", "person")

    # Should have rows for each person
    assert len(result) == 3
    # Should have household data merged in
    assert "household_id" in result.columns
    assert "person_id" in result.columns
    assert "rent" in result.columns


def test_map_household_to_benunit():
    """Test mapping household-level data to benunit level."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "benunit_id": [1, 1, 2, 2],
                "household_id": [1, 1, 2, 2],
                "person_weight": [1.0, 1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame({"benunit_id": [1, 2], "benunit_weight": [1.0, 1.0]}),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "rent": [1000, 800],
                "household_weight": [1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    data = UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    )

    result = data.map_to_entity("household", "benunit")

    # Should have benunit and household data
    assert "benunit_id" in result.columns
    assert "household_id" in result.columns
    assert "rent" in result.columns


def test_map_with_column_selection():
    """Test mapping with specific column selection."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "age": [30, 25, 40],
                "income": [50000, 30000, 60000],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame({"benunit_id": [1, 2], "benunit_weight": [1.0, 1.0]}),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame({"household_id": [1, 2], "household_weight": [1.0, 1.0]}),
        weights="household_weight",
    )

    data = UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    )

    # Map only age to household
    result = data.map_to_entity("person", "household", columns=["age"])

    assert "age" in result.columns
    assert "household_id" in result.columns
    # income should not be included
    assert "income" not in result.columns


def test_invalid_entity_names():
    """Test that invalid entity names raise ValueError."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1],
                "benunit_id": [1],
                "household_id": [1],
                "person_weight": [1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame({"benunit_id": [1], "benunit_weight": [1.0]}),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame({"household_id": [1], "household_weight": [1.0]}),
        weights="household_weight",
    )

    data = UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    )

    with pytest.raises(ValueError, match="Invalid source entity"):
        data.map_to_entity("invalid", "person")

    with pytest.raises(ValueError, match="Invalid target entity"):
        data.map_to_entity("person", "invalid")
