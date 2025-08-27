"""Base class for economic impact report using proper calculations."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from ..countries.general import ModelOutput
    from ..database.models import ReportMetadata
    from sqlalchemy.orm import Session

from .calculations import (
    calculate_decile_impacts,
    calculate_poverty_impacts,
    calculate_inequality_impacts,
    calculate_budgetary_impacts,
)


class EconomicImpactReportBase(ABC):
    """Base class for country-specific economic impact report."""
    
    def __init__(self, session: "Session", report_metadata: "ReportMetadata"):
        """Initialise the report.
        
        Args:
            session: Database session for writing results
            report_metadata: Metadata for this report run
        """
        self.session = session
        self.report = report_metadata
        self.country = report_metadata.country.lower()
        
    @abstractmethod
    def calculate_all_impacts(self, baseline: "ModelOutput", comparison: "ModelOutput") -> None:
        """Calculate all economic impacts and populate database tables.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison/reform simulation output
        """
        pass
    
    def calculate_and_store_decile_impacts(self, baseline: "ModelOutput", comparison: "ModelOutput", by_wealth: bool = False) -> None:
        """Calculate and store decile impacts using microdf.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison simulation output
            by_wealth: Whether to calculate by wealth decile (UK only)
        """
        from ..database.models import DecileImpact
        
        # Calculate impacts using the new function
        impacts = calculate_decile_impacts(baseline, comparison, by_wealth)
        
        decile_type = "wealth" if by_wealth else "income"
        
        # Store in database
        for decile, data in impacts.items():
            impact = DecileImpact(
                report_id=self.report.id,
                decile_type=decile_type,
                decile=int(decile),
                relative_change=data['relative_change'],
                average_change=data['average_change'],
                lose_more_than_5_percent=data['winners_losers']['lose_more_than_5_percent'],
                lose_less_than_5_percent=data['winners_losers']['lose_less_than_5_percent'],
                no_change=data['winners_losers']['no_change'],
                gain_less_than_5_percent=data['winners_losers']['gain_less_than_5_percent'],
                gain_more_than_5_percent=data['winners_losers']['gain_more_than_5_percent'],
            )
            self.session.add(impact)
    
    def calculate_and_store_poverty_impacts(self, baseline: "ModelOutput", comparison: "ModelOutput") -> None:
        """Calculate and store poverty impacts.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison simulation output
        """
        from ..database.models import PovertyImpact
        
        # Calculate impacts using the new function
        impacts = calculate_poverty_impacts(baseline, comparison)
        
        # Store in database
        for key, data in impacts.items():
            group_type, group_value = key.split('_', 1)
            
            impact = PovertyImpact(
                report_id=self.report.id,
                group_type=group_type,
                group_value=group_value,
                poverty_rate_baseline=data['poverty']['baseline'],
                poverty_rate_reform=data['poverty']['reform'],
                poverty_rate_change=data['poverty']['change'],
                deep_poverty_rate_baseline=data['deep_poverty']['baseline'],
                deep_poverty_rate_reform=data['deep_poverty']['reform'],
                deep_poverty_rate_change=data['deep_poverty']['change'],
            )
            self.session.add(impact)
    
    def calculate_and_store_inequality_impacts(self, baseline: "ModelOutput", comparison: "ModelOutput") -> None:
        """Calculate and store inequality impacts.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison simulation output
        """
        from ..database.models import InequalityImpact
        
        # Calculate impacts using the new function
        impacts = calculate_inequality_impacts(baseline, comparison)
        
        # Store in database
        impact = InequalityImpact(
            report_id=self.report.id,
            gini_baseline=impacts['gini']['baseline'],
            gini_reform=impacts['gini']['reform'],
            gini_change=impacts['gini']['change'],
            top_10_percent_share_baseline=impacts['top_10_percent_share']['baseline'],
            top_10_percent_share_reform=impacts['top_10_percent_share']['reform'],
            top_10_percent_share_change=impacts['top_10_percent_share']['change'],
            top_1_percent_share_baseline=impacts['top_1_percent_share']['baseline'],
            top_1_percent_share_reform=impacts['top_1_percent_share']['reform'],
            top_1_percent_share_change=impacts['top_1_percent_share']['change'],
        )
        self.session.add(impact)
    
    def calculate_and_store_budgetary_impacts(self, baseline: "ModelOutput", comparison: "ModelOutput") -> None:
        """Calculate and store budgetary impacts.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison simulation output
        """
        from ..database.models import BudgetaryImpact
        
        # Calculate impacts using the new function
        impacts = calculate_budgetary_impacts(baseline, comparison)
        
        # Store in database
        impact = BudgetaryImpact(
            report_id=self.report.id,
            budgetary_impact=impacts['budgetary_impact'],
            tax_revenue_impact=impacts['tax_revenue_impact'],
            state_tax_revenue_impact=impacts['state_tax_revenue_impact'],
            benefit_spending_impact=impacts['benefit_spending_impact'],
            households_affected=impacts['households_affected'],
            baseline_net_income=impacts['baseline_net_income'],
        )
        self.session.add(impact)