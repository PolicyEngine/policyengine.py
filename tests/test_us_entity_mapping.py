import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.tax_benefit_models.us import USYearData


def test_map_same_entity():
    """Test mapping from an entity to itself returns the same data."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "household_id": [1, 1, 2],
                "tax_unit_id": [1, 1, 2],
                "age": [30, 25, 40],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame({"household_id": [1, 2], "household_weight": [1.0, 1.0]}),
        weights="household_weight",
    )

    tax_unit_df = MicroDataFrame(
        pd.DataFrame({"tax_unit_id": [1, 2], "tax_unit_weight": [1.0, 1.0]}),
        weights="tax_unit_weight",
    )

    marital_unit_df = MicroDataFrame(
        pd.DataFrame(
            {"marital_unit_id": [1, 2], "marital_unit_weight": [1.0, 1.0]}
        ),
        weights="marital_unit_weight",
    )

    family_df = MicroDataFrame(
        pd.DataFrame({"family_id": [1, 2], "family_weight": [1.0, 1.0]}),
        weights="family_weight",
    )

    spm_unit_df = MicroDataFrame(
        pd.DataFrame({"spm_unit_id": [1, 2], "spm_unit_weight": [1.0, 1.0]}),
        weights="spm_unit_weight",
    )

    data = USYearData(
        person=person_df,
        household=household_df,
        tax_unit=tax_unit_df,
        marital_unit=marital_unit_df,
        family=family_df,
        spm_unit=spm_unit_df,
    )

    # Test person -> person
    result = data.map_to_entity("person", "person")
    assert isinstance(result, MicroDataFrame)
    assert len(result) == 3
    assert list(result["person_id"]) == [1, 2, 3]


def test_map_person_to_household_aggregates():
    """Test mapping person-level data to household level aggregates correctly."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "household_id": [1, 1, 2, 2],
                "tax_unit_id": [1, 1, 2, 2],
                "income": [50000, 30000, 60000, 40000],
                "person_weight": [1.0, 1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
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

    tax_unit_df = MicroDataFrame(
        pd.DataFrame({"tax_unit_id": [1, 2], "tax_unit_weight": [1.0, 1.0]}),
        weights="tax_unit_weight",
    )

    marital_unit_df = MicroDataFrame(
        pd.DataFrame(
            {"marital_unit_id": [1, 2], "marital_unit_weight": [1.0, 1.0]}
        ),
        weights="marital_unit_weight",
    )

    family_df = MicroDataFrame(
        pd.DataFrame({"family_id": [1, 2], "family_weight": [1.0, 1.0]}),
        weights="family_weight",
    )

    spm_unit_df = MicroDataFrame(
        pd.DataFrame({"spm_unit_id": [1, 2], "spm_unit_weight": [1.0, 1.0]}),
        weights="spm_unit_weight",
    )

    data = USYearData(
        person=person_df,
        household=household_df,
        tax_unit=tax_unit_df,
        marital_unit=marital_unit_df,
        family=family_df,
        spm_unit=spm_unit_df,
    )

    result = data.map_to_entity("person", "household", columns=["income"])

    # Should return household-level data
    assert isinstance(result, MicroDataFrame)
    assert len(result) == 2

    # Income should be aggregated (summed) at household level
    assert "income" in result.columns
    household_incomes = result.set_index("household_id")["income"].to_dict()
    assert household_incomes[1] == 80000  # 50000 + 30000
    assert household_incomes[2] == 100000  # 60000 + 40000


def test_map_household_to_person_expands():
    """Test mapping household-level data to person level expands correctly."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "household_id": [1, 1, 2],
                "tax_unit_id": [1, 1, 2],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
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

    tax_unit_df = MicroDataFrame(
        pd.DataFrame({"tax_unit_id": [1, 2], "tax_unit_weight": [1.0, 1.0]}),
        weights="tax_unit_weight",
    )

    marital_unit_df = MicroDataFrame(
        pd.DataFrame(
            {"marital_unit_id": [1, 2], "marital_unit_weight": [1.0, 1.0]}
        ),
        weights="marital_unit_weight",
    )

    family_df = MicroDataFrame(
        pd.DataFrame({"family_id": [1, 2], "family_weight": [1.0, 1.0]}),
        weights="family_weight",
    )

    spm_unit_df = MicroDataFrame(
        pd.DataFrame({"spm_unit_id": [1, 2], "spm_unit_weight": [1.0, 1.0]}),
        weights="spm_unit_weight",
    )

    data = USYearData(
        person=person_df,
        household=household_df,
        tax_unit=tax_unit_df,
        marital_unit=marital_unit_df,
        family=family_df,
        spm_unit=spm_unit_df,
    )

    result = data.map_to_entity("household", "person", columns=["rent"])

    # Should have rows for each person
    assert len(result) == 3
    # Should have household data merged in (replicated)
    assert "household_id" in result.columns
    assert "person_id" in result.columns
    assert "rent" in result.columns

    # Rent should be replicated to all persons in household
    person_rents = result.set_index("person_id")["rent"].to_dict()
    assert person_rents[1] == 1000  # Person 1 in household 1
    assert person_rents[2] == 1000  # Person 2 in household 1
    assert person_rents[3] == 800  # Person 3 in household 2


def test_map_tax_unit_to_household_via_person():
    """Test mapping tax_unit to household goes through person and aggregates."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "household_id": [1, 1, 2, 2],
                "tax_unit_id": [1, 1, 2, 3],
                "person_weight": [1.0, 1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame({"household_id": [1, 2], "household_weight": [1.0, 1.0]}),
        weights="household_weight",
    )

    tax_unit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "tax_unit_id": [1, 2, 3],
                "taxable_income": [80000, 60000, 40000],
                "tax_unit_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="tax_unit_weight",
    )

    marital_unit_df = MicroDataFrame(
        pd.DataFrame(
            {"marital_unit_id": [1, 2], "marital_unit_weight": [1.0, 1.0]}
        ),
        weights="marital_unit_weight",
    )

    family_df = MicroDataFrame(
        pd.DataFrame({"family_id": [1, 2], "family_weight": [1.0, 1.0]}),
        weights="family_weight",
    )

    spm_unit_df = MicroDataFrame(
        pd.DataFrame({"spm_unit_id": [1, 2], "spm_unit_weight": [1.0, 1.0]}),
        weights="spm_unit_weight",
    )

    data = USYearData(
        person=person_df,
        household=household_df,
        tax_unit=tax_unit_df,
        marital_unit=marital_unit_df,
        family=family_df,
        spm_unit=spm_unit_df,
    )

    result = data.map_to_entity(
        "tax_unit", "household", columns=["taxable_income"]
    )

    # Should return household-level data
    assert len(result) == 2
    assert "taxable_income" in result.columns

    # Income should be aggregated at household level
    # Household 1 has tax_unit 1 (80000)
    # Household 2 has tax_unit 2 (60000) and tax_unit 3 (40000) = 100000
    household_incomes = result.set_index("household_id")[
        "taxable_income"
    ].to_dict()
    assert household_incomes[1] == 80000
    assert household_incomes[2] == 100000


def test_invalid_entity_names():
    """Test that invalid entity names raise ValueError."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1],
                "household_id": [1],
                "tax_unit_id": [1],
                "person_weight": [1.0],
            }
        ),
        weights="person_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame({"household_id": [1], "household_weight": [1.0]}),
        weights="household_weight",
    )

    tax_unit_df = MicroDataFrame(
        pd.DataFrame({"tax_unit_id": [1], "tax_unit_weight": [1.0]}),
        weights="tax_unit_weight",
    )

    marital_unit_df = MicroDataFrame(
        pd.DataFrame({"marital_unit_id": [1], "marital_unit_weight": [1.0]}),
        weights="marital_unit_weight",
    )

    family_df = MicroDataFrame(
        pd.DataFrame({"family_id": [1], "family_weight": [1.0]}),
        weights="family_weight",
    )

    spm_unit_df = MicroDataFrame(
        pd.DataFrame({"spm_unit_id": [1], "spm_unit_weight": [1.0]}),
        weights="spm_unit_weight",
    )

    data = USYearData(
        person=person_df,
        household=household_df,
        tax_unit=tax_unit_df,
        marital_unit=marital_unit_df,
        family=family_df,
        spm_unit=spm_unit_df,
    )

    with pytest.raises(ValueError, match="Invalid source entity"):
        data.map_to_entity("invalid", "person")

    with pytest.raises(ValueError, match="Invalid target entity"):
        data.map_to_entity("person", "invalid")
