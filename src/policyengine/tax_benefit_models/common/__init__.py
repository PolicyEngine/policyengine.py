"""Country-agnostic helpers for household calculation and reform analysis.

The country modules (:mod:`policyengine.tax_benefit_models.us`,
:mod:`policyengine.tax_benefit_models.uk`) thread these helpers through
their public ``calculate_household`` / ``analyze_reform`` entry points.
"""

from .axes import normalize_axes as normalize_axes
from .axes import values_for_entity as values_for_entity
from .extra_variables import dispatch_extra_variables as dispatch_extra_variables
from .model_version import (
    MicrosimulationModelVersion as MicrosimulationModelVersion,
)
from .reform import compile_reform as compile_reform
from .reform import compile_reform_to_dynamic as compile_reform_to_dynamic
from .reform import compile_reform_to_policy as compile_reform_to_policy
from .result import EntityResult as EntityResult
from .result import HouseholdResult as HouseholdResult
