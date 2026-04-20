"""Tests for the `_build_entity_relationships` helper on the country models.

Scoping/filtering behaviour is covered by ``tests/test_scoping_strategy.py``.
"""


class TestUSBuildEntityRelationships:
    """US model `_build_entity_relationships`."""

    def test__given_us_dataset__then_has_all_entity_id_columns(self, us_test_dataset):
        from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)
        entity_rel = model._build_entity_relationships(us_test_dataset)
        assert set(entity_rel.columns) == {
            "person_id",
            "household_id",
            "tax_unit_id",
            "spm_unit_id",
            "family_id",
            "marital_unit_id",
        }

    def test__given_us_dataset__then_row_count_equals_person_count(
        self, us_test_dataset
    ):
        from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)
        entity_rel = model._build_entity_relationships(us_test_dataset)
        assert len(entity_rel) == 6

    def test__given_us_dataset__then_mappings_preserved(self, us_test_dataset):
        from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)
        entity_rel = model._build_entity_relationships(us_test_dataset)
        person_1_row = entity_rel[entity_rel["person_id"] == 1].iloc[0]
        assert person_1_row["household_id"] == 1
        assert person_1_row["tax_unit_id"] == 1


class TestUKBuildEntityRelationships:
    """UK model `_build_entity_relationships`."""

    def test__given_uk_dataset__then_has_all_entity_id_columns(self, uk_test_dataset):
        from policyengine.tax_benefit_models.uk.model import PolicyEngineUKLatest

        model = PolicyEngineUKLatest.__new__(PolicyEngineUKLatest)
        entity_rel = model._build_entity_relationships(uk_test_dataset)
        assert set(entity_rel.columns) == {
            "person_id",
            "benunit_id",
            "household_id",
        }

    def test__given_uk_dataset__then_row_count_equals_person_count(
        self, uk_test_dataset
    ):
        from policyengine.tax_benefit_models.uk.model import PolicyEngineUKLatest

        model = PolicyEngineUKLatest.__new__(PolicyEngineUKLatest)
        entity_rel = model._build_entity_relationships(uk_test_dataset)
        assert len(entity_rel) == 6
