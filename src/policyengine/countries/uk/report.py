"""UK-specific economic impact report."""

from typing import TYPE_CHECKING
from ...report.base import EconomicImpactReportBase

if TYPE_CHECKING:
    from .model_output import UKModelOutput


class UKEconomicImpactReport(EconomicImpactReportBase):
    """UK-specific economic impact report."""
    
    def calculate_all_impacts(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        """Calculate all UK economic impacts and populate database tables.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison/reform simulation output
        """
        # Update report status
        from ...database.models import SimulationStatus
        self.report.status = SimulationStatus.RUNNING
        self.session.commit()
        
        try:
            # Calculate standard impacts
            self.calculate_and_store_decile_impacts(baseline, comparison, by_wealth=False)
            
            # UK also supports wealth deciles
            if self._has_wealth_data(baseline):
                self.calculate_and_store_decile_impacts(baseline, comparison, by_wealth=True)
            
            self.calculate_and_store_poverty_impacts(baseline, comparison)
            self.calculate_and_store_inequality_impacts(baseline, comparison)
            self.calculate_and_store_budgetary_impacts(baseline, comparison)
            
            # UK-specific: Program impacts
            self.calculate_program_impacts(baseline, comparison)
            
            # Mark as completed
            from datetime import datetime
            self.report.status = SimulationStatus.COMPLETED
            self.report.completed_at = datetime.now()
            self.session.commit()
            
        except Exception as e:
            # Mark as failed
            self.report.status = SimulationStatus.FAILED
            self.session.commit()
            raise e
    
    def _has_wealth_data(self, data: "UKModelOutput") -> bool:
        """Check if wealth data is available."""
        return "total_wealth" in data.household.columns or "household_wealth_decile" in data.household.columns
    
    def calculate_program_impacts(self, baseline: "UKModelOutput", comparison: "UKModelOutput") -> None:
        """Calculate UK-specific program impacts.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison simulation output
        """
        from ...database.models import ProgramSpecificImpact
        
        # List of UK benefit programs to track
        uk_programs = [
            "universal_credit",
            "child_benefit",
            "income_support",
            "housing_benefit",
            "pension_credit",
            "state_pension",
            "employment_support_allowance",
            "jobseekers_allowance",
            "child_tax_credit",
            "working_tax_credit",
        ]
        
        baseline_hh = baseline.household
        comparison_hh = comparison.household
        
        if "household_weight" in baseline_hh.columns:
            weights = baseline_hh["household_weight"].values
        else:
            weights = 1
        
        for program in uk_programs:
            # Check if program exists in data
            if program not in baseline_hh.columns:
                continue
            
            baseline_cost = (baseline_hh[program].values * weights).sum()
            comparison_cost = (comparison_hh[program].values * weights).sum()
            
            impact = ProgramSpecificImpact(
                report_id=self.report.id,
                program_name=program,
                baseline_cost=float(baseline_cost),
                reform_cost=float(comparison_cost),
                cost_difference=float(comparison_cost - baseline_cost),
            )
            self.session.add(impact)