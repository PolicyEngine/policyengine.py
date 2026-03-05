"""Country-specific region definitions.

This package contains region registries for each supported country.
"""

from .uk.regions import uk_region_registry
from .us.regions import us_region_registry

__all__ = ["us_region_registry", "uk_region_registry"]
