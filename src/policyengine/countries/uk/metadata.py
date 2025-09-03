from policyengine_uk.tax_benefit_system import system
from policyengine.utils.metadata import get_metadata
from policyengine.countries.uk.datasets import create_efrs

def get_uk_metadata():
    md = get_metadata(system, country="uk")

    # Add country datasets: efrs_2023_24 .. efrs_2030_31 (inclusive)
    datasets = []
    for end_year in range(2024, 2031):
        start_year = end_year - 1
        name = f"efrs_{start_year}_{str(end_year)[2:]}"
        ds = create_efrs(year=end_year)
        ds.name = name
        datasets.append(ds)

    md["datasets"] = datasets
    return md
