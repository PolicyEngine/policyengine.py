from policyengine_us.system import system
from policyengine.utils.metadata import get_metadata
from policyengine.countries.us.datasets import create_ecps_years


def get_us_metadata():
    """Return US model metadata (variables, parameters, values) only."""
    return get_metadata(system, country="us")


def get_us_datasets(start_year: int = 2024, end_year: int = 2035):
    """Return US dataset rows for the given range (default 2024–2035)."""
    return create_ecps_years(start_year, end_year)
