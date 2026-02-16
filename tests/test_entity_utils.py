"""Tests for shared entity utilities and reform dict helpers."""

import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.utils.entity_utils import (
    build_entity_relationships,
    filter_dataset_by_household_variable,
)
from policyengine.utils.parametric_reforms import (
    build_reform_dict,
    merge_reform_dicts,
)


class TestBuildEntityRelationships:
    """Tests for the shared build_entity_relationships function."""

    def test__given_us_style_entities__then_returns_all_columns(
        self, us_test_dataset
    ):
        """Given: Person data with 5 group entities (US style)
        When: Building entity relationships
        Then: DataFrame has person_id + all 5 entity ID columns
        """
        person_data = pd.DataFrame(us_test_dataset.data.person)
        group_entities = [
            "household",
            "tax_unit",
            "spm_unit",
            "family",
            "marital_unit",
        ]

        result = build_entity_relationships(person_data, group_entities)

        expected_columns = {
            "person_id",
            "household_id",
            "tax_unit_id",
            "spm_unit_id",
            "family_id",
            "marital_unit_id",
        }
        assert set(result.columns) == expected_columns

    def test__given_uk_style_entities__then_returns_all_columns(
        self, uk_test_dataset
    ):
        """Given: Person data with 2 group entities (UK style)
        When: Building entity relationships
        Then: DataFrame has person_id + 2 entity ID columns
        """
        person_data = pd.DataFrame(uk_test_dataset.data.person)
        group_entities = ["benunit", "household"]

        result = build_entity_relationships(person_data, group_entities)

        expected_columns = {"person_id", "benunit_id", "household_id"}
        assert set(result.columns) == expected_columns

    def test__given_6_persons__then_returns_6_rows(self, us_test_dataset):
        """Given: Dataset with 6 persons
        When: Building entity relationships
        Then: Result has 6 rows
        """
        person_data = pd.DataFrame(us_test_dataset.data.person)

        result = build_entity_relationships(
            person_data, ["household", "tax_unit"]
        )

        assert len(result) == 6

    def test__given_prefixed_columns__then_resolves_correctly(self):
        """Given: Person data with person_household_id naming convention
        When: Building entity relationships
        Then: Correctly maps to household_id in result
        """
        person_data = pd.DataFrame(
            {
                "person_id": [1, 2],
                "person_household_id": [10, 20],
            }
        )

        result = build_entity_relationships(person_data, ["household"])

        assert list(result["household_id"]) == [10, 20]

    def test__given_bare_columns__then_resolves_correctly(self):
        """Given: Person data with household_id naming convention (no prefix)
        When: Building entity relationships
        Then: Correctly maps to household_id in result
        """
        person_data = pd.DataFrame(
            {
                "person_id": [1, 2],
                "household_id": [10, 20],
            }
        )

        result = build_entity_relationships(person_data, ["household"])

        assert list(result["household_id"]) == [10, 20]


class TestFilterDatasetByHouseholdVariable:
    """Tests for the shared filter_dataset_by_household_variable function."""

    def test__given_matching_value__then_returns_filtered_entities(self):
        """Given: Dataset with 2 places
        When: Filtering by place_fips=44000
        Then: Returns only matching households and related persons
        """
        entity_data = {
            "person": MicroDataFrame(
                pd.DataFrame(
                    {
                        "person_id": [1, 2, 3],
                        "household_id": [1, 1, 2],
                        "person_weight": [1.0, 1.0, 1.0],
                    }
                ),
                weights="person_weight",
            ),
            "household": MicroDataFrame(
                pd.DataFrame(
                    {
                        "household_id": [1, 2],
                        "household_weight": [1.0, 1.0],
                        "place": ["A", "B"],
                    }
                ),
                weights="household_weight",
            ),
        }

        result = filter_dataset_by_household_variable(
            entity_data=entity_data,
            group_entities=["household"],
            variable_name="place",
            variable_value="A",
        )

        assert len(pd.DataFrame(result["person"])) == 2
        assert len(pd.DataFrame(result["household"])) == 1

    def test__given_no_match__then_raises_value_error(self):
        """Given: Dataset with no matching households
        When: Filtering
        Then: Raises ValueError
        """
        entity_data = {
            "person": MicroDataFrame(
                pd.DataFrame(
                    {
                        "person_id": [1],
                        "household_id": [1],
                        "person_weight": [1.0],
                    }
                ),
                weights="person_weight",
            ),
            "household": MicroDataFrame(
                pd.DataFrame(
                    {
                        "household_id": [1],
                        "household_weight": [1.0],
                        "place": ["A"],
                    }
                ),
                weights="household_weight",
            ),
        }

        with pytest.raises(ValueError, match="No households found"):
            filter_dataset_by_household_variable(
                entity_data=entity_data,
                group_entities=["household"],
                variable_name="place",
                variable_value="Z",
            )

    def test__given_missing_variable__then_raises_value_error(self):
        """Given: Dataset without the filter variable
        When: Filtering
        Then: Raises ValueError
        """
        entity_data = {
            "person": MicroDataFrame(
                pd.DataFrame(
                    {
                        "person_id": [1],
                        "household_id": [1],
                        "person_weight": [1.0],
                    }
                ),
                weights="person_weight",
            ),
            "household": MicroDataFrame(
                pd.DataFrame(
                    {
                        "household_id": [1],
                        "household_weight": [1.0],
                    }
                ),
                weights="household_weight",
            ),
        }

        with pytest.raises(ValueError, match="not found in household data"):
            filter_dataset_by_household_variable(
                entity_data=entity_data,
                group_entities=["household"],
                variable_name="nonexistent",
                variable_value="x",
            )


class TestBuildReformDict:
    """Tests for build_reform_dict helper."""

    def test__given_none__then_returns_none(self):
        assert build_reform_dict(None) is None

    def test__given_no_parameter_values__then_returns_none(self):
        from unittest.mock import MagicMock

        obj = MagicMock()
        obj.parameter_values = []
        assert build_reform_dict(obj) is None

    def test__given_parameter_values__then_returns_reform_dict(self):
        from datetime import datetime
        from unittest.mock import MagicMock

        param = MagicMock()
        param.name = "gov.test.param"

        pv = MagicMock()
        pv.parameter = param
        pv.value = 1000
        pv.start_date = datetime(2024, 1, 1)
        pv.end_date = None

        obj = MagicMock()
        obj.parameter_values = [pv]

        result = build_reform_dict(obj)

        assert result == {"gov.test.param": {"2024-01-01": 1000}}


class TestMergeReformDicts:
    """Tests for merge_reform_dicts helper."""

    def test__given_both_none__then_returns_none(self):
        assert merge_reform_dicts(None, None) is None

    def test__given_base_none__then_returns_override(self):
        override = {"param": {"2024-01-01": 100}}
        assert merge_reform_dicts(None, override) is override

    def test__given_override_none__then_returns_base(self):
        base = {"param": {"2024-01-01": 100}}
        assert merge_reform_dicts(base, None) is base

    def test__given_both_dicts__then_merges_correctly(self):
        base = {"param_a": {"2024-01-01": 100}}
        override = {"param_b": {"2024-01-01": 200}}

        result = merge_reform_dicts(base, override)

        assert result == {
            "param_a": {"2024-01-01": 100},
            "param_b": {"2024-01-01": 200},
        }

    def test__given_overlapping_params__then_override_wins(self):
        base = {"param": {"2024-01-01": 100}}
        override = {"param": {"2024-01-01": 999}}

        result = merge_reform_dicts(base, override)

        assert result == {"param": {"2024-01-01": 999}}

    def test__given_merge__then_does_not_mutate_base(self):
        base = {"param": {"2024-01-01": 100}}
        override = {"param": {"2024-01-01": 999}}

        merge_reform_dicts(base, override)

        assert base == {"param": {"2024-01-01": 100}}
