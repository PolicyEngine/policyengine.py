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
    """Test mapping person-level data to benunit level aggregates correctly."""
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

    result = data.map_to_entity("person", "benunit", columns=["income"])

    # Should return a MicroDataFrame
    assert isinstance(result, MicroDataFrame)
    # Should have rows for each benunit (aggregated)
    assert len(result) == 2
    # Should have benunit data with aggregated income
    assert "benunit_id" in result.columns
    assert "income" in result.columns

    # Income should be aggregated (summed) at benunit level
    benunit_incomes = result.set_index("benunit_id")["income"].to_dict()
    assert benunit_incomes[1] == 80000  # 50000 + 30000
    assert benunit_incomes[2] == 60000  # 60000


def test_map_person_to_household():
    """Test mapping person-level data to household level aggregates correctly."""
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

    result = data.map_to_entity("person", "household", columns=["income"])

    # Should have rows for each household (aggregated)
    assert len(result) == 2
    # Should have household data with aggregated income
    assert "household_id" in result.columns
    assert "income" in result.columns

    # Income should be aggregated (summed) at household level
    household_incomes = result.set_index("household_id")["income"].to_dict()
    assert household_incomes[1] == 80000  # 50000 + 30000
    assert household_incomes[2] == 60000  # 60000


def test_map_benunit_to_person():
    """Test mapping benunit-level data to person level expands correctly."""
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

    result = data.map_to_entity("benunit", "person", columns=["total_benefit"])

    # Should have rows for each person
    assert len(result) == 3
    # Should have benunit data merged in (expanded/replicated)
    assert "benunit_id" in result.columns
    assert "person_id" in result.columns
    assert "total_benefit" in result.columns

    # Benefit should be replicated to all persons in benunit
    person_benefits = result.set_index("person_id")["total_benefit"].to_dict()
    assert person_benefits[1] == 1000  # Person 1 in benunit 1
    assert person_benefits[2] == 1000  # Person 2 in benunit 1
    assert person_benefits[3] == 500  # Person 3 in benunit 2


def test_map_benunit_to_household():
    """Test mapping benunit-level data to household level aggregates via person."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "benunit_id": [1, 1, 2, 3],
                "household_id": [1, 1, 2, 2],
                "person_weight": [1.0, 1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2, 3],
                "total_benefit": [1000, 500, 300],
                "benunit_weight": [1.0, 1.0, 1.0],
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

    result = data.map_to_entity(
        "benunit", "household", columns=["total_benefit"]
    )

    # Should have household data (aggregated)
    assert len(result) == 2
    assert "household_id" in result.columns
    assert "total_benefit" in result.columns

    # Benefits should be aggregated at household level
    # Household 1 has benunit 1 (1000)
    # Household 2 has benunit 2 (500) and benunit 3 (300) = 800
    household_benefits = result.set_index("household_id")[
        "total_benefit"
    ].to_dict()
    assert household_benefits[1] == 1000
    assert household_benefits[2] == 800


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
    """Test mapping household-level data to benunit level expands via person."""
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

    result = data.map_to_entity("household", "benunit", columns=["rent"])

    # Should have benunit data (expanded from household via person)
    # Since benunit-household is 1:1 in this case, should have 2 rows
    assert len(result) == 2
    assert "benunit_id" in result.columns
    assert "rent" in result.columns

    # Rent should be mapped from household to benunit
    benunit_rents = result.set_index("benunit_id")["rent"].to_dict()
    assert benunit_rents[1] == 1000  # Benunit 1 in household 1
    assert benunit_rents[2] == 800  # Benunit 2 in household 2


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

    # Map only age to household (aggregated)
    result = data.map_to_entity("person", "household", columns=["age"])

    assert "age" in result.columns
    assert "household_id" in result.columns
    # income should not be included
    assert "income" not in result.columns
    # Should be aggregated to household level
    assert len(result) == 2


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
