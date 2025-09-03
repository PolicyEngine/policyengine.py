from policyengine_us.system import system
from policyengine.utils.metadata import get_metadata

def get_us_metadata():
    return get_metadata(system, country="us")
