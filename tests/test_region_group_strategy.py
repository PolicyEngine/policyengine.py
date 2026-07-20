"""Tests for RegionGroupStrategy — scoping to the union of several regions."""

import pandas as pd
import pytest
from pydantic import TypeAdapter

from policyengine.core.scoping_strategy import (
    RegionGroupStrategy,
    RowFilterStrategy,
    ScopingStrategy,
)


def _hh_ids(result):
    return set(pd.DataFrame(result["household"])["household_id"])


def _state(value):
    return RowFilterStrategy(variable_name="state_fips", variable_value=value)


class TestRegionGroupStrategy:
    def test__has_region_group_strategy_type(self):
        assert RegionGroupStrategy(members=[_state(6)]).strategy_type == "region_group"

    def test__apply_unions_members(self, us_entity_data, us_group_entities):
        # CA (households 1,2) ∪ NJ (household 3) == all households.
        strategy = RegionGroupStrategy(members=[_state(6), _state(34)])
        result = strategy.apply(
            entity_data=us_entity_data, group_entities=us_group_entities, year=2024
        )
        assert _hh_ids(result) == {1, 2, 3}
        assert set(pd.DataFrame(result["person"])["person_id"]) == {1, 2, 3, 4, 5, 6}

    def test__single_member_group_matches_row_filter(
        self, us_entity_data, us_group_entities
    ):
        grouped = RegionGroupStrategy(members=[_state(34)]).apply(
            entity_data=us_entity_data, group_entities=us_group_entities, year=2024
        )
        row = _state(34).apply(
            entity_data=us_entity_data, group_entities=us_group_entities, year=2024
        )
        assert _hh_ids(grouped) == _hh_ids(row) == {3}

    def test__disjoint_union_has_no_duplicates(self, us_entity_data, us_group_entities):
        strategy = RegionGroupStrategy(members=[_state(6), _state(34)])
        result = strategy.apply(
            entity_data=us_entity_data, group_entities=us_group_entities, year=2024
        )
        household = pd.DataFrame(result["household"])
        assert len(household) == 3
        assert household["household_id"].is_unique

    def test__overlapping_members_are_not_double_counted(
        self, us_entity_data, us_group_entities
    ):
        # CA (state_fips=6 -> households 1,2) overlaps CA-01 (geoid 601 -> hh 1).
        strategy = RegionGroupStrategy(
            members=[
                _state(6),
                RowFilterStrategy(
                    variable_name="congressional_district_geoid", variable_value=601
                ),
            ]
        )
        result = strategy.apply(
            entity_data=us_entity_data, group_entities=us_group_entities, year=2024
        )
        household = pd.DataFrame(result["household"])
        assert _hh_ids(result) == {1, 2}  # household 1 counted once, not twice
        assert household["household_id"].is_unique

    def test__uk_country_group(self, uk_entity_data, uk_group_entities):
        # ENGLAND (households 1,2) ∪ SCOTLAND (household 3) == all UK households.
        strategy = RegionGroupStrategy(
            members=[
                RowFilterStrategy(variable_name="country", variable_value="ENGLAND"),
                RowFilterStrategy(variable_name="country", variable_value="SCOTLAND"),
            ]
        )
        result = strategy.apply(
            entity_data=uk_entity_data, group_entities=uk_group_entities, year=2024
        )
        assert _hh_ids(result) == {1, 2, 3}

    def test__member_additional_filters_are_applied(
        self, us_entity_data, us_group_entities
    ):
        # CA households additionally filtered to CD 601 -> only household 1.
        member = RowFilterStrategy(
            variable_name="state_fips",
            variable_value=6,
            additional_filters={"congressional_district_geoid": 601},
        )
        result = RegionGroupStrategy(members=[member]).apply(
            entity_data=us_entity_data, group_entities=us_group_entities, year=2024
        )
        assert _hh_ids(result) == {1}

    def test__empty_union_raises(self, us_entity_data, us_group_entities):
        strategy = RegionGroupStrategy(members=[_state(99)])  # no such state
        with pytest.raises(ValueError, match="No households match"):
            strategy.apply(
                entity_data=us_entity_data, group_entities=us_group_entities, year=2024
            )

    def test__cache_key_is_member_order_independent(self):
        a = RegionGroupStrategy(members=[_state(6), _state(34)])
        b = RegionGroupStrategy(members=[_state(34), _state(6)])
        assert a.cache_key == b.cache_key
        assert "region_group" in a.cache_key

    def test__roundtrips_through_scoping_strategy_union(self):
        strategy = RegionGroupStrategy(members=[_state(6), _state(34)])
        restored = TypeAdapter(ScopingStrategy).validate_python(strategy.model_dump())
        assert isinstance(restored, RegionGroupStrategy)
        assert restored.strategy_type == "region_group"
        assert len(restored.members) == 2

    def test__requires_at_least_one_member(self):
        with pytest.raises(ValueError):
            RegionGroupStrategy(members=[])
