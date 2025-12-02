import logging
from collections import OrderedDict

import psutil

logger = logging.getLogger(__name__)

_MEMORY_THRESHOLDS_GB = [8, 16, 32]
_warned_thresholds: set[int] = set()


class LRUCache[T]:
    """Least-recently-used cache with configurable size limit and memory monitoring."""

    def __init__(self, max_size: int = 100):
        self._max_size = max_size
        self._cache: OrderedDict[str, T] = OrderedDict()

    def get(self, key: str) -> T | None:
        """Get item from cache, marking it as recently used."""
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def add(self, key: str, value: T) -> None:
        """Add item to cache with LRU eviction when full."""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            self._cache[key] = value
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

        self._check_memory_usage()

    def clear(self) -> None:
        """Clear all items from cache."""
        self._cache.clear()
        _warned_thresholds.clear()

    def __len__(self) -> int:
        return len(self._cache)

    def _check_memory_usage(self) -> None:
        """Check memory usage and warn at threshold crossings."""
        process = psutil.Process()
        memory_gb = process.memory_info().rss / (1024**3)

        for threshold in _MEMORY_THRESHOLDS_GB:
            if memory_gb >= threshold and threshold not in _warned_thresholds:
                logger.warning(
                    f"Memory usage has reached {memory_gb:.2f}GB (threshold: {threshold}GB). "
                    f"Cache contains {len(self._cache)} items."
                )
                _warned_thresholds.add(threshold)
