"""UK-specific economic impact report."""

from typing import TYPE_CHECKING
from ...report.base import EconomicImpactReportBase

if TYPE_CHECKING:
    from .model_output import UKModelOutput


class UKEconomicImpactReport(EconomicImpactReportBase):
    """UK-specific economic impact report."""
    
    def calculate_all_impacts(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        pass