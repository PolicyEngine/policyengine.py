from policyengine_us.system import system
from policyengine.utils.metadata import get_metadata
from policyengine.countries.us.datasets import create_ecps_years

def get_us_metadata():
    md = get_metadata(system, country="us")

    datasets = create_ecps_years(2024, 2035)

    md["datasets"] = datasets
    return md
