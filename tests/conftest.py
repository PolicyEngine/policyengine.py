"""Pytest configuration and shared fixtures."""

# Import fixtures from fixtures module so pytest can discover them
from tests.fixtures.region_fixtures import (  # noqa: F401
    empty_registry,
    sample_registry,
)
