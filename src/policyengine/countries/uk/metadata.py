from policyengine_uk.tax_benefit_system import system
from policyengine.utils.metadata import get_metadata
from policyengine.countries.uk.datasets import create_efrs_years

def get_uk_metadata():
    md = get_metadata(system, country="uk")

    datasets = create_efrs_years(2023, 2030)

    md["datasets"] = datasets
    return md
