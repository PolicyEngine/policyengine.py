try:
    from policyengine_uk.tax_benefit_system import system

    UK_AVAILABLE = True
except ImportError:
    UK_AVAILABLE = False
    system = None

from policyengine.utils.metadata import get_metadata
from policyengine.countries.uk.datasets import create_efrs_years


def get_uk_metadata():
    """Return UK model metadata (variables, parameters, values) only."""
    if not UK_AVAILABLE:
        raise ImportError(
            "policyengine-uk is not installed. "
            "Install it with: pip install 'policyengine[uk]' or pip install policyengine-uk"
        )
    return get_metadata(system, country="uk")


def get_uk_datasets(start_year: int = 2023, end_year: int = 2030):
    """Return UK dataset rows for the given range (default 2023–2030)."""
    return create_efrs_years(start_year, end_year)
