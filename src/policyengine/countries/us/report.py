"""US-specific economic impact report."""

from typing import TYPE_CHECKING
from ...report.base import EconomicImpactReportBase

if TYPE_CHECKING:
    from .model_output import USModelOutput


class USEconomicImpactReport(EconomicImpactReportBase):
    """US-specific economic impact report."""
    
    def calculate_all_impacts(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate all US economic impacts and populate database tables.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison/reform simulation output
        """
        pass