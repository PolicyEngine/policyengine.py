"""Country-agnostic helpers for household calculation and reform analysis.

The country modules (:mod:`policyengine.tax_benefit_models.us`,
:mod:`policyengine.tax_benefit_models.uk`) thread these helpers through
their public ``calculate_household`` / ``analyze_reform`` entry points.
"""

from .extra_variables import dispatch_extra_variables as dispatch_extra_variables
from .model_version import (
    MicrosimulationModelVersion as MicrosimulationModelVersion,
)
from .reform import compile_reform as compile_reform
from .result import EntityResult as EntityResult
from .result import HouseholdResult as HouseholdResult
