from policyengine_us.system import system
from policyengine.utils.metadata import get_metadata
from policyengine.countries.us.datasets import create_ecps

def get_us_metadata():
    md = get_metadata(system, country="us")

    # Add country datasets: ecps_2023 and 2024 .. 2035
    datasets = []
    years = [2023] + list(range(2024, 2036))
    for year in years:
        name = f"ecps_{year}"
        ds = create_ecps(year=year)
        ds.name = name
        datasets.append(ds)

    md["datasets"] = datasets
    return md
