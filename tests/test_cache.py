import os
import tempfile

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.core.cache import LRUCache
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest,
)


def test_simulation_cache_hit():
    """Test that simulation caching works with UK simulations."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "age": [30, 25, 40],
                "employment_income": [50000, 30000, 60000],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.h5")

        dataset = PolicyEngineUKDataset(
            name="Test",
            description="Test dataset",
            filepath=filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=dataset,
        )

        # Import the cache
        from policyengine.core.simulation import _cache

        # Manually add to cache (simulating what ensure() does)
        _cache.add(simulation.id, simulation)

        # Verify simulation is in cache
        assert simulation.id in _cache._cache
        assert len(_cache) >= 1

        # Verify cache returns same object
        cached_sim = _cache.get(simulation.id)
        assert cached_sim is simulation

        # Clear cache for other tests
        _cache.clear()


def test_lru_cache_eviction():
    """Test that LRU cache properly evicts old items."""
    cache = LRUCache[str](max_size=3)

    cache.add("a", "value_a")
    cache.add("b", "value_b")
    cache.add("c", "value_c")

    assert len(cache) == 3
    assert cache.get("a") == "value_a"

    # Add fourth item, should evict 'b' (least recently used)
    cache.add("d", "value_d")

    assert len(cache) == 3
    assert cache.get("b") is None
    assert cache.get("a") == "value_a"
    assert cache.get("c") == "value_c"
    assert cache.get("d") == "value_d"


def test_lru_cache_access_updates_order():
    """Test that accessing items updates their position in LRU order."""
    cache = LRUCache[str](max_size=3)

    cache.add("a", "value_a")
    cache.add("b", "value_b")
    cache.add("c", "value_c")

    # Access 'a' to move it to most recently used
    cache.get("a")

    # Add fourth item, should evict 'b' (now least recently used)
    cache.add("d", "value_d")

    assert cache.get("a") == "value_a"
    assert cache.get("b") is None
    assert cache.get("c") == "value_c"
    assert cache.get("d") == "value_d"


def test_lru_cache_clear():
    """Test that clearing cache works properly."""
    cache = LRUCache[str](max_size=10)

    cache.add("a", "value_a")
    cache.add("b", "value_b")
    cache.add("c", "value_c")

    assert len(cache) == 3

    cache.clear()

    assert len(cache) == 0
    assert cache.get("a") is None
    assert cache.get("b") is None
    assert cache.get("c") is None
