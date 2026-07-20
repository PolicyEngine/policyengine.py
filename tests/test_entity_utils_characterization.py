"""Characterization tests locking the exact multi-entity cascade of
``filter_dataset_by_household_variable`` BEFORE the household-ID-set refactor.

These pin the behavior the refactor must preserve byte-for-byte: filtering by a
household variable keeps exactly the matching households and cascades to persons
and every group entity consistently. Uses the ``us_test_dataset`` fixture
(households 1,2 = state_fips 6 / CA; household 3 = state_fips 34 / NJ).
"""

import pandas as pd
import pytest

from policyengine.utils.entity_utils import filter_dataset_by_household_variable

US_GROUP_ENTITIES = ["household", "tax_unit", "spm_unit", "family", "marital_unit"]


def _entity_data(dataset):
    data = dataset.data
    return {entity: getattr(data, entity) for entity in ["person", *US_GROUP_ENTITIES]}


def _ids(result, entity):
    return set(pd.DataFrame(result[entity])[f"{entity}_id"])


class TestFilterCascadeCharacterization:
    def test__filter_ca__keeps_ca_households_and_cascades(self, us_test_dataset):
        result = filter_dataset_by_household_variable(
            entity_data=_entity_data(us_test_dataset),
            group_entities=US_GROUP_ENTITIES,
            variable_name="state_fips",
            variable_value=6,
        )
        assert _ids(result, "household") == {1, 2}
        assert set(pd.DataFrame(result["person"])["person_id"]) == {1, 2, 3, 4}
        assert _ids(result, "tax_unit") == {1, 2}
        assert _ids(result, "spm_unit") == {1, 2}
        assert _ids(result, "family") == {1, 2}
        assert _ids(result, "marital_unit") == {1, 2}

    def test__filter_nj__keeps_nj_household_and_cascades(self, us_test_dataset):
        result = filter_dataset_by_household_variable(
            entity_data=_entity_data(us_test_dataset),
            group_entities=US_GROUP_ENTITIES,
            variable_name="state_fips",
            variable_value=34,
        )
        assert _ids(result, "household") == {3}
        assert set(pd.DataFrame(result["person"])["person_id"]) == {5, 6}
        assert _ids(result, "tax_unit") == {3}
        assert _ids(result, "marital_unit") == {3}

    def test__filter_preserves_national_weights(self, us_test_dataset):
        result = filter_dataset_by_household_variable(
            entity_data=_entity_data(us_test_dataset),
            group_entities=US_GROUP_ENTITIES,
            variable_name="state_fips",
            variable_value=6,
        )
        household = pd.DataFrame(result["household"])
        # National weights preserved (not reweighted): CA = 1000 + 1000.
        assert float(household["household_weight"].sum()) == 2000.0

    def test__no_match_raises_value_error(self, us_test_dataset):
        with pytest.raises(ValueError, match="No households found"):
            filter_dataset_by_household_variable(
                entity_data=_entity_data(us_test_dataset),
                group_entities=US_GROUP_ENTITIES,
                variable_name="state_fips",
                variable_value=99,
            )

    def test__congressional_district_filter_cascades(self, us_test_dataset):
        # CD 601 is household 1 only (persons 1,2).
        result = filter_dataset_by_household_variable(
            entity_data=_entity_data(us_test_dataset),
            group_entities=US_GROUP_ENTITIES,
            variable_name="congressional_district_geoid",
            variable_value=601,
        )
        assert _ids(result, "household") == {1}
        assert set(pd.DataFrame(result["person"])["person_id"]) == {1, 2}
