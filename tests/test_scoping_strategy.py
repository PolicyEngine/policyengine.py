"""Tests for region scoping strategies."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.core.scoping_strategy import (
    RowFilterStrategy,
    ScopingStrategy,
    WeightReplacementStrategy,
)
from policyengine.core.simulation import Simulation


class TestRowFilterStrategy:
    """Tests for RowFilterStrategy."""

    def test__given_row_filter__then_has_correct_strategy_type(self):
        strategy = RowFilterStrategy(
            variable_name="country", variable_value="ENGLAND"
        )
        assert strategy.strategy_type == "row_filter"

    def test__given_row_filter__then_serialization_roundtrip_works(self):
        strategy = RowFilterStrategy(
            variable_name="place_fips", variable_value="44000"
        )
        json_str = strategy.model_dump_json()
        restored = RowFilterStrategy.model_validate_json(json_str)
        assert restored.variable_name == "place_fips"
        assert restored.variable_value == "44000"
        assert restored.strategy_type == "row_filter"

    def test__given_row_filter__then_apply_filters_correctly(
        self, uk_test_entity_data
    ):
        strategy = RowFilterStrategy(
            variable_name="country", variable_value="ENGLAND"
        )
        result = strategy.apply(
            entity_data=uk_test_entity_data,
            group_entities=["benunit", "household"],
            year=2024,
        )
        household_df = pd.DataFrame(result["household"])
        assert len(household_df) == 2
        assert all(household_df["country"] == "ENGLAND")

    def test__given_row_filter__then_cache_key_is_descriptive(self):
        strategy = RowFilterStrategy(
            variable_name="country", variable_value="ENGLAND"
        )
        assert "row_filter" in strategy.cache_key
        assert "country" in strategy.cache_key
        assert "ENGLAND" in strategy.cache_key


class TestWeightReplacementStrategy:
    """Tests for WeightReplacementStrategy."""

    def test__given_weight_replacement__then_has_correct_strategy_type(self):
        strategy = WeightReplacementStrategy(
            weight_matrix_bucket="test-bucket",
            weight_matrix_key="weights.h5",
            lookup_csv_bucket="test-bucket",
            lookup_csv_key="lookup.csv",
            region_code="E14001234",
        )
        assert strategy.strategy_type == "weight_replacement"

    def test__given_weight_replacement__then_serialization_roundtrip_works(
        self,
    ):
        strategy = WeightReplacementStrategy(
            weight_matrix_bucket="policyengine-uk-data-private",
            weight_matrix_key="parliamentary_constituency_weights.h5",
            lookup_csv_bucket="policyengine-uk-data-private",
            lookup_csv_key="constituencies_2024.csv",
            region_code="E14001234",
        )
        json_str = strategy.model_dump_json()
        restored = WeightReplacementStrategy.model_validate_json(json_str)
        assert restored.weight_matrix_bucket == "policyengine-uk-data-private"
        assert restored.region_code == "E14001234"
        assert restored.strategy_type == "weight_replacement"

    @patch("policyengine_core.tools.google_cloud.download_gcs_file")
    def test__given_weight_replacement__then_apply_replaces_weights(
        self, mock_download, uk_test_entity_data, tmp_path
    ):
        # Set up mock lookup CSV
        lookup_csv_path = tmp_path / "lookup.csv"
        lookup_df = pd.DataFrame(
            {
                "code": ["R001", "R002", "R003"],
                "name": ["Region A", "Region B", "Region C"],
            }
        )
        lookup_df.to_csv(lookup_csv_path, index=False)

        # Set up mock weight matrix (3 regions x 3 households)
        weights_h5_path = tmp_path / "weights.h5"
        import h5py

        with h5py.File(weights_h5_path, "w") as f:
            # Region R002 (index 1) gets weights [500, 300, 200]
            f.create_dataset(
                "2024",
                data=np.array(
                    [
                        [100.0, 200.0, 300.0],
                        [500.0, 300.0, 200.0],
                        [150.0, 250.0, 350.0],
                    ]
                ),
            )

        mock_download.side_effect = lambda bucket, file_path: (
            str(lookup_csv_path)
            if file_path.endswith(".csv")
            else str(weights_h5_path)
        )

        strategy = WeightReplacementStrategy(
            weight_matrix_bucket="test-bucket",
            weight_matrix_key="weights.h5",
            lookup_csv_bucket="test-bucket",
            lookup_csv_key="lookup.csv",
            region_code="R002",
        )

        result = strategy.apply(
            entity_data=uk_test_entity_data,
            group_entities=["benunit", "household"],
            year=2024,
        )

        # Household weights should be replaced
        household_df = pd.DataFrame(result["household"])
        np.testing.assert_array_almost_equal(
            household_df["household_weight"].values, [500.0, 300.0, 200.0]
        )

        # All 3 households should still be present (not filtered)
        assert len(household_df) == 3

        # All 6 persons should still be present
        person_df = pd.DataFrame(result["person"])
        assert len(person_df) == 6

    @patch("policyengine_core.tools.google_cloud.download_gcs_file")
    def test__given_weight_replacement__then_raises_on_dimension_mismatch(
        self, mock_download, uk_test_entity_data, tmp_path
    ):
        lookup_csv_path = tmp_path / "lookup.csv"
        pd.DataFrame({"code": ["R001"], "name": ["Region A"]}).to_csv(
            lookup_csv_path, index=False
        )

        # Weight matrix with wrong number of households (2 instead of 3)
        weights_h5_path = tmp_path / "weights.h5"
        import h5py

        with h5py.File(weights_h5_path, "w") as f:
            f.create_dataset("2024", data=np.array([[100.0, 200.0]]))

        mock_download.side_effect = lambda bucket, file_path: (
            str(lookup_csv_path)
            if file_path.endswith(".csv")
            else str(weights_h5_path)
        )

        strategy = WeightReplacementStrategy(
            weight_matrix_bucket="test-bucket",
            weight_matrix_key="weights.h5",
            lookup_csv_bucket="test-bucket",
            lookup_csv_key="lookup.csv",
            region_code="R001",
        )

        with pytest.raises(ValueError, match="Weight matrix row length"):
            strategy.apply(
                entity_data=uk_test_entity_data,
                group_entities=["benunit", "household"],
                year=2024,
            )

    def test__given_weight_replacement__then_cache_key_is_descriptive(self):
        strategy = WeightReplacementStrategy(
            weight_matrix_bucket="test-bucket",
            weight_matrix_key="weights.h5",
            lookup_csv_bucket="test-bucket",
            lookup_csv_key="lookup.csv",
            region_code="E14001234",
        )
        assert "weight_replacement" in strategy.cache_key
        assert "weights.h5" in strategy.cache_key
        assert "E14001234" in strategy.cache_key

    def test__given_lookup_csv_with_code_column__then_finds_region_by_code(
        self,
    ):
        lookup_df = pd.DataFrame(
            {"code": ["A", "B", "C"], "name": ["Foo", "Bar", "Baz"]}
        )
        idx = WeightReplacementStrategy._find_region_index(lookup_df, "B")
        assert idx == 1

    def test__given_lookup_csv_with_name_column__then_finds_region_by_name(
        self,
    ):
        lookup_df = pd.DataFrame(
            {"code": ["A", "B", "C"], "name": ["Foo", "Bar", "Baz"]}
        )
        idx = WeightReplacementStrategy._find_region_index(lookup_df, "Bar")
        assert idx == 1

    def test__given_lookup_csv_without_match__then_raises_value_error(self):
        lookup_df = pd.DataFrame(
            {"code": ["A", "B"], "name": ["Foo", "Bar"]}
        )
        with pytest.raises(ValueError, match="not found in lookup CSV"):
            WeightReplacementStrategy._find_region_index(
                lookup_df, "NONEXISTENT"
            )


class TestScopingStrategyDiscriminatedUnion:
    """Tests for the discriminated union type alias."""

    def test__given_row_filter_json__then_deserializes_to_correct_type(self):
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ScopingStrategy)
        strategy = adapter.validate_json(
            '{"strategy_type": "row_filter", "variable_name": "country", "variable_value": "ENGLAND"}'
        )
        assert isinstance(strategy, RowFilterStrategy)
        assert strategy.variable_name == "country"

    def test__given_weight_replacement_json__then_deserializes_to_correct_type(
        self,
    ):
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ScopingStrategy)
        strategy = adapter.validate_json(
            '{"strategy_type": "weight_replacement", '
            '"weight_matrix_bucket": "bucket", "weight_matrix_key": "key.h5", '
            '"lookup_csv_bucket": "bucket", "lookup_csv_key": "lookup.csv", '
            '"region_code": "E14001234"}'
        )
        assert isinstance(strategy, WeightReplacementStrategy)
        assert strategy.region_code == "E14001234"

    def test__given_different_strategies__then_cache_keys_are_distinct(self):
        row_filter = RowFilterStrategy(
            variable_name="country", variable_value="ENGLAND"
        )
        weight_replacement = WeightReplacementStrategy(
            weight_matrix_bucket="bucket",
            weight_matrix_key="key.h5",
            lookup_csv_bucket="bucket",
            lookup_csv_key="lookup.csv",
            region_code="E14001234",
        )
        assert row_filter.cache_key != weight_replacement.cache_key


class TestSimulationScopingStrategy:
    """Tests for scoping_strategy on the Simulation model."""

    def test__given_no_strategy__then_simulation_has_none(self):
        sim = Simulation()
        assert sim.scoping_strategy is None

    def test__given_explicit_strategy__then_simulation_stores_it(self):
        strategy = RowFilterStrategy(
            variable_name="country", variable_value="ENGLAND"
        )
        sim = Simulation(scoping_strategy=strategy)
        assert sim.scoping_strategy is not None
        assert isinstance(sim.scoping_strategy, RowFilterStrategy)

    def test__given_legacy_filter_fields__then_auto_constructs_row_filter(
        self,
    ):
        sim = Simulation(
            filter_field="place_fips",
            filter_value="44000",
        )
        assert sim.scoping_strategy is not None
        assert isinstance(sim.scoping_strategy, RowFilterStrategy)
        assert sim.scoping_strategy.variable_name == "place_fips"
        assert sim.scoping_strategy.variable_value == "44000"

    def test__given_explicit_strategy_and_legacy_fields__then_explicit_wins(
        self,
    ):
        explicit = WeightReplacementStrategy(
            weight_matrix_bucket="bucket",
            weight_matrix_key="key.h5",
            lookup_csv_bucket="bucket",
            lookup_csv_key="lookup.csv",
            region_code="E14001234",
        )
        sim = Simulation(
            scoping_strategy=explicit,
            filter_field="household_weight",
            filter_value="E14001234",
        )
        assert isinstance(sim.scoping_strategy, WeightReplacementStrategy)

    def test__given_only_filter_field_no_value__then_no_auto_construct(self):
        sim = Simulation(filter_field="place_fips")
        assert sim.scoping_strategy is None


# Fixtures for scoping strategy tests
@pytest.fixture
def uk_test_entity_data() -> dict[str, MicroDataFrame]:
    """Create minimal UK entity data for scoping strategy tests."""
    person_data = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5, 6],
            "benunit_id": [1, 1, 2, 2, 3, 3],
            "household_id": [1, 1, 2, 2, 3, 3],
            "person_weight": [
                1000.0,
                1000.0,
                1000.0,
                1000.0,
                1000.0,
                1000.0,
            ],
            "age": [35, 30, 45, 40, 25, 28],
        }
    )
    benunit_data = pd.DataFrame(
        {
            "benunit_id": [1, 2, 3],
            "benunit_weight": [1000.0, 1000.0, 1000.0],
        }
    )
    household_data = pd.DataFrame(
        {
            "household_id": [1, 2, 3],
            "household_weight": [1000.0, 1000.0, 1000.0],
            "country": ["ENGLAND", "ENGLAND", "SCOTLAND"],
        }
    )
    return {
        "person": MicroDataFrame(person_data, weights="person_weight"),
        "benunit": MicroDataFrame(benunit_data, weights="benunit_weight"),
        "household": MicroDataFrame(
            household_data, weights="household_weight"
        ),
    }
