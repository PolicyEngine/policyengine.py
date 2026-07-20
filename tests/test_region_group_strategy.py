"""Tests for RegionGroupStrategy — scoping to the union of several regions."""

import pandas as pd
import pytest
from pydantic import TypeAdapter

from policyengine.core.scoping_strategy import (
    RegionGroupStrategy,
    RowFilterStrategy,
    ScopingStrategy,
)

US_GROUP_ENTITIES = ["household", "tax_unit", "spm_unit", "family", "marital_unit"]


def _entity_data(dataset):
    data = dataset.data
    return {entity: getattr(data, entity) for entity in ["person", *US_GROUP_ENTITIES]}


def _hh_ids(result):
    return set(pd.DataFrame(result["household"])["household_id"])


def _member(value):
    return RowFilterStrategy(variable_name="state_fips", variable_value=value)


class TestRegionGroupStrategy:
    def test__has_region_group_strategy_type(self):
        assert RegionGroupStrategy(members=[_member(6)]).strategy_type == "region_group"

    def test__apply_unions_members(self, us_test_dataset):
        # CA (households 1,2) ∪ NJ (household 3) == all households.
        strategy = RegionGroupStrategy(members=[_member(6), _member(34)])
        result = strategy.apply(
            entity_data=_entity_data(us_test_dataset),
            group_entities=US_GROUP_ENTITIES,
            year=2024,
        )
        assert _hh_ids(result) == {1, 2, 3}
        assert set(pd.DataFrame(result["person"])["person_id"]) == {1, 2, 3, 4, 5, 6}

    def test__single_member_group_matches_row_filter(self, us_test_dataset):
        entity_data = _entity_data(us_test_dataset)
        grouped = RegionGroupStrategy(members=[_member(34)]).apply(
            entity_data=entity_data, group_entities=US_GROUP_ENTITIES, year=2024
        )
        row = RowFilterStrategy(variable_name="state_fips", variable_value=34).apply(
            entity_data=entity_data, group_entities=US_GROUP_ENTITIES, year=2024
        )
        assert _hh_ids(grouped) == _hh_ids(row) == {3}

    def test__disjoint_union_has_no_duplicates(self, us_test_dataset):
        strategy = RegionGroupStrategy(members=[_member(6), _member(34)])
        result = strategy.apply(
            entity_data=_entity_data(us_test_dataset),
            group_entities=US_GROUP_ENTITIES,
            year=2024,
        )
        household = pd.DataFrame(result["household"])
        assert len(household) == 3
        assert household["household_id"].is_unique

    def test__cache_key_is_member_order_independent(self):
        a = RegionGroupStrategy(members=[_member(6), _member(34)])
        b = RegionGroupStrategy(members=[_member(34), _member(6)])
        assert a.cache_key == b.cache_key
        assert "region_group" in a.cache_key

    def test__roundtrips_through_scoping_strategy_union(self):
        strategy = RegionGroupStrategy(members=[_member(6), _member(34)])
        restored = TypeAdapter(ScopingStrategy).validate_python(strategy.model_dump())
        assert isinstance(restored, RegionGroupStrategy)
        assert restored.strategy_type == "region_group"
        assert len(restored.members) == 2

    def test__requires_at_least_one_member(self):
        with pytest.raises(ValueError):
            RegionGroupStrategy(members=[])
