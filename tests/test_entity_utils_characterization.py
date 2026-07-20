"""Characterization tests for the household filter cascade, plus direct tests of
``filter_dataset_by_household_ids`` (the id-set "Job B" reused by the group).

These pin the behavior the household-ID-set refactor must preserve: filtering
keeps exactly the matching households and cascades to persons and every group
entity consistently. Uses the ``us_test_dataset`` fixture (households 1,2 =
state_fips 6 / CA; household 3 = state_fips 34 / NJ).
"""

import pandas as pd
import pytest

from policyengine.utils.entity_utils import (
    filter_dataset_by_household_ids,
    filter_dataset_by_household_variable,
)


def _ids(result, entity):
    return set(pd.DataFrame(result[entity])[f"{entity}_id"])


class TestFilterCascadeCharacterization:
    def test__filter_ca__keeps_ca_households_and_cascades(
        self, us_entity_data, us_group_entities
    ):
        result = filter_dataset_by_household_variable(
            entity_data=us_entity_data,
            group_entities=us_group_entities,
            variable_name="state_fips",
            variable_value=6,
        )
        assert _ids(result, "household") == {1, 2}
        assert set(pd.DataFrame(result["person"])["person_id"]) == {1, 2, 3, 4}
        assert _ids(result, "tax_unit") == {1, 2}
        assert _ids(result, "spm_unit") == {1, 2}
        assert _ids(result, "family") == {1, 2}
        assert _ids(result, "marital_unit") == {1, 2}

    def test__filter_nj__keeps_nj_household_and_cascades(
        self, us_entity_data, us_group_entities
    ):
        result = filter_dataset_by_household_variable(
            entity_data=us_entity_data,
            group_entities=us_group_entities,
            variable_name="state_fips",
            variable_value=34,
        )
        assert _ids(result, "household") == {3}
        assert set(pd.DataFrame(result["person"])["person_id"]) == {5, 6}
        assert _ids(result, "tax_unit") == {3}
        assert _ids(result, "marital_unit") == {3}

    def test__filter_preserves_national_weights(
        self, us_entity_data, us_group_entities
    ):
        result = filter_dataset_by_household_variable(
            entity_data=us_entity_data,
            group_entities=us_group_entities,
            variable_name="state_fips",
            variable_value=6,
        )
        household = pd.DataFrame(result["household"])
        # National weights preserved (not reweighted): CA = 1000 + 1000.
        assert float(household["household_weight"].sum()) == 2000.0

    def test__no_match_raises_value_error(self, us_entity_data, us_group_entities):
        with pytest.raises(ValueError, match="No households found"):
            filter_dataset_by_household_variable(
                entity_data=us_entity_data,
                group_entities=us_group_entities,
                variable_name="state_fips",
                variable_value=99,
            )

    def test__congressional_district_filter_cascades(
        self, us_entity_data, us_group_entities
    ):
        # CD 601 is household 1 only (persons 1,2).
        result = filter_dataset_by_household_variable(
            entity_data=us_entity_data,
            group_entities=us_group_entities,
            variable_name="congressional_district_geoid",
            variable_value=601,
        )
        assert _ids(result, "household") == {1}
        assert set(pd.DataFrame(result["person"])["person_id"]) == {1, 2}


class TestFilterDatasetByHouseholdIds:
    """Direct tests of the id-set entry point reused by RegionGroupStrategy."""

    def test__explicit_ids_cascade_to_all_entities(
        self, us_entity_data, us_group_entities
    ):
        result = filter_dataset_by_household_ids(
            us_entity_data, us_group_entities, {1, 3}
        )
        assert _ids(result, "household") == {1, 3}
        assert set(pd.DataFrame(result["person"])["person_id"]) == {1, 2, 5, 6}
        assert _ids(result, "tax_unit") == {1, 3}

    def test__accepts_any_iterable_and_dedupes(self, us_entity_data, us_group_entities):
        result = filter_dataset_by_household_ids(
            us_entity_data, us_group_entities, [1, 1, 2]
        )
        assert _ids(result, "household") == {1, 2}

    def test__empty_selection_raises(self, us_entity_data, us_group_entities):
        with pytest.raises(
            ValueError, match="No households match the requested household id set"
        ):
            filter_dataset_by_household_ids(us_entity_data, us_group_entities, set())
