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
        # Update report status
        from ...database.models import SimulationStatus
        self.report.status = SimulationStatus.RUNNING
        self.session.commit()
        
        try:
            # Calculate standard impacts
            self.calculate_and_store_decile_impacts(baseline, comparison, by_wealth=False)
            
            self.calculate_and_store_poverty_impacts(baseline, comparison)
            self.calculate_and_store_inequality_impacts(baseline, comparison)
            self.calculate_and_store_budgetary_impacts(baseline, comparison)
            
            # US-specific: Racial poverty breakdown
            self.calculate_racial_poverty_breakdown(baseline, comparison)
            
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
    
    def calculate_racial_poverty_breakdown(self, baseline: "USModelOutput", comparison: "USModelOutput") -> None:
        """Calculate US-specific racial poverty breakdown.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison simulation output
        """
        from ...database.models import PovertyImpact
        import numpy as np
        
        # Get person data
        baseline_person = baseline.person
        comparison_person = comparison.person
        
        # Check if race data is available
        if "race" not in baseline_person.columns:
            return
        
        # Get weights
        if "person_weight" in baseline_person.columns:
            weights = baseline_person["person_weight"].values
        else:
            weights = np.ones(len(baseline_person))
        
        # Check for poverty variables
        if "person_in_poverty" not in baseline_person.columns:
            return
        
        baseline_poverty = baseline_person["person_in_poverty"].values
        comparison_poverty = comparison_person["person_in_poverty"].values
        
        # Deep poverty (if available)
        if "person_in_deep_poverty" in baseline_person.columns:
            baseline_deep = baseline_person["person_in_deep_poverty"].values
            comparison_deep = comparison_person["person_in_deep_poverty"].values
        else:
            baseline_deep = None
            comparison_deep = None
        
        race = baseline_person["race"].values
        
        race_groups = [
            ("race", "white", race == "WHITE"),
            ("race", "black", race == "BLACK"),
            ("race", "hispanic", race == "HISPANIC"),
            ("race", "other", race == "OTHER"),
        ]
        
        for group_type, group_value, mask in race_groups:
            group_weights = weights[mask]
            total_weight = np.sum(group_weights)
            
            if total_weight > 0:
                poverty_baseline = np.sum(baseline_poverty[mask] * group_weights) / total_weight
                poverty_reform = np.sum(comparison_poverty[mask] * group_weights) / total_weight
                
                if baseline_deep is not None:
                    deep_baseline = np.sum(baseline_deep[mask] * group_weights) / total_weight
                    deep_reform = np.sum(comparison_deep[mask] * group_weights) / total_weight
                else:
                    deep_baseline = deep_reform = None
            else:
                poverty_baseline = poverty_reform = 0
                deep_baseline = deep_reform = None
            
            impact = PovertyImpact(
                report_id=self.report.id,
                group_type=group_type,
                group_value=group_value,
                poverty_rate_baseline=float(poverty_baseline),
                poverty_rate_reform=float(poverty_reform),
                poverty_rate_change=float(poverty_reform - poverty_baseline),
                deep_poverty_rate_baseline=float(deep_baseline) if deep_baseline is not None else None,
                deep_poverty_rate_reform=float(deep_reform) if deep_reform is not None else None,
                deep_poverty_rate_change=float(deep_reform - deep_baseline) if deep_baseline is not None and deep_reform is not None else None,
            )
            self.session.add(impact)