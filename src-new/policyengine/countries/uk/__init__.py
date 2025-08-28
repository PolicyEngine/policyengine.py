"""UK-specific PolicyEngine components."""

from .model_output import UKModelOutput, process_uk_simulation, UK_VARIABLE_WHITELIST
from .report import UKEconomicImpactReport

__all__ = [
    "UKModelOutput",
    "process_uk_simulation", 
    "UK_VARIABLE_WHITELIST",
    "UKEconomicImpactReport",
]