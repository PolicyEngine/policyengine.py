from policyengine_uk.tax_benefit_system import system
from policyengine.utils.metadata import get_metadata

def get_uk_metadata():
    return get_metadata(system, country="uk")
