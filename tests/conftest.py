"""Pytest configuration and shared fixtures."""

# Import fixtures from fixtures module so pytest can discover them
from tests.fixtures.filtering_fixtures import (  # noqa: F401
    uk_test_dataset,
    us_test_dataset,
)
from tests.fixtures.region_fixtures import (  # noqa: F401
    empty_registry,
    sample_registry,
)
