"""US geographic data definitions.

This module provides static data for US geographic regions:
- states.py: State abbreviations and full names
- districts.py: Congressional district counts by state
- places.py: US Census places (cities/towns over 100K population)
"""

from .districts import AT_LARGE_STATES, DISTRICT_COUNTS
from .places import US_PLACES
from .states import US_STATES

__all__ = [
    "US_STATES",
    "DISTRICT_COUNTS",
    "AT_LARGE_STATES",
    "US_PLACES",
]
