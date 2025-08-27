"""Report manager for economic impact analysis."""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from ..countries.general import ModelOutput
    from ..countries.uk import UKModelOutput
    from ..countries.us import USModelOutput

from .models import (
    ReportMetadata,
    SimulationMetadata,
    SimulationStatus,
    DecileImpact,
    PovertyImpact,
    InequalityImpact,
    BudgetaryImpact,
    LaborSupplyImpact,
    ProgramSpecificImpact,
)


class ReportManager:
    """Manages economic impact reports in the database."""
    
    def __init__(self, session: Session):
        """Initialise the report manager.
        
        Args:
            session: Database session
        """
        self.session = session
    
    def create_report(
        self,
        name: str,
        baseline_simulation_id: str,
        comparison_simulation_id: str,
        country: str,
        year: Optional[int] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> ReportMetadata:
        """Create a new report metadata entry.
        
        Args:
            name: Name of the report
            baseline_simulation_id: ID of baseline simulation
            comparison_simulation_id: ID of comparison/reform simulation
            country: Country code
            year: Year of analysis (optional for multi-year)
            description: Report description
            tags: List of tags for filtering
            created_by: User ID who created the report
            
        Returns:
            Created report metadata
        """
        report = ReportMetadata(
            name=name,
            baseline_simulation_id=baseline_simulation_id,
            comparison_simulation_id=comparison_simulation_id,
            country=country,
            year=year,
            description=description,
            tags=tags,
            created_by=created_by,
        )
        self.session.add(report)
        self.session.commit()
        return report
    
    def run_report(
        self,
        report_id: str,
        baseline_output: "ModelOutput",
        comparison_output: "ModelOutput",
    ) -> None:
        """Run economic impact analysis and populate report tables.
        
        Args:
            report_id: ID of the report to run
            baseline_output: Baseline simulation output
            comparison_output: Comparison/reform simulation output
        """
        # Get report metadata
        report = self.session.query(ReportMetadata).filter_by(id=report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Import report classes directly from country modules
        from ..countries.uk.report import UKEconomicImpactReport
        from ..countries.us.report import USEconomicImpactReport
        
        # Create appropriate report instance
        if report.country.lower() == "uk":
            reporter = UKEconomicImpactReport(self.session, report)
        elif report.country.lower() == "us":
            reporter = USEconomicImpactReport(self.session, report)
        else:
            raise ValueError(f"Unsupported country: {report.country}")
        
        # Run the analysis
        reporter.calculate_all_impacts(baseline_output, comparison_output)
    
    def get_report(self, report_id: str) -> Optional[ReportMetadata]:
        """Get a report by ID.
        
        Args:
            report_id: Report ID
            
        Returns:
            Report metadata or None
        """
        return self.session.query(ReportMetadata).filter_by(id=report_id).first()
    
    def list_reports(
        self,
        country: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[SimulationStatus] = None,
    ) -> List[ReportMetadata]:
        """List reports with optional filters.
        
        Args:
            country: Filter by country
            year: Filter by year
            status: Filter by status
            
        Returns:
            List of report metadata
        """
        query = self.session.query(ReportMetadata)
        
        if country:
            query = query.filter_by(country=country)
        if year:
            query = query.filter_by(year=year)
        if status:
            query = query.filter_by(status=status)
        
        return query.all()
    
    def get_report_results(self, report_id: str) -> dict:
        """Get all results for a report.
        
        Args:
            report_id: Report ID
            
        Returns:
            Dictionary containing all report results
        """
        report = self.get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        results = {
            "metadata": {
                "id": report.id,
                "name": report.name,
                "country": report.country,
                "year": report.year,
                "status": report.status.value if report.status else None,
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "completed_at": report.completed_at.isoformat() if report.completed_at else None,
            },
            "decile_impacts": self._get_decile_impacts(report_id),
            "poverty_impacts": self._get_poverty_impacts(report_id),
            "inequality_impact": self._get_inequality_impact(report_id),
            "budgetary_impact": self._get_budgetary_impact(report_id),
            "labor_supply_impact": self._get_labor_supply_impact(report_id),
        }
        
        # Add UK-specific program impacts if available
        if report.country.lower() == "uk":
            results["program_impacts"] = self._get_program_impacts(report_id)
        
        return results
    
    def _get_decile_impacts(self, report_id: str) -> dict:
        """Get decile impacts for a report."""
        impacts = self.session.query(DecileImpact).filter_by(report_id=report_id).all()
        
        result = {"income": {}, "wealth": {}}
        for impact in impacts:
            decile_data = {
                "relative_change": impact.relative_change,
                "average_change": impact.average_change,
                "winners_losers": {
                    "lose_more_than_5_percent": impact.lose_more_than_5_percent,
                    "lose_less_than_5_percent": impact.lose_less_than_5_percent,
                    "no_change": impact.no_change,
                    "gain_less_than_5_percent": impact.gain_less_than_5_percent,
                    "gain_more_than_5_percent": impact.gain_more_than_5_percent,
                }
            }
            result[impact.decile_type][impact.decile] = decile_data
        
        return result
    
    def _get_poverty_impacts(self, report_id: str) -> dict:
        """Get poverty impacts for a report."""
        impacts = self.session.query(PovertyImpact).filter_by(report_id=report_id).all()
        
        result = {}
        for impact in impacts:
            if impact.group_type not in result:
                result[impact.group_type] = {}
            
            result[impact.group_type][impact.group_value] = {
                "poverty": {
                    "baseline": impact.poverty_rate_baseline,
                    "reform": impact.poverty_rate_reform,
                    "change": impact.poverty_rate_change,
                },
                "deep_poverty": {
                    "baseline": impact.deep_poverty_rate_baseline,
                    "reform": impact.deep_poverty_rate_reform,
                    "change": impact.deep_poverty_rate_change,
                }
            }
        
        return result
    
    def _get_inequality_impact(self, report_id: str) -> dict:
        """Get inequality impact for a report."""
        impact = self.session.query(InequalityImpact).filter_by(report_id=report_id).first()
        
        if not impact:
            return {}
        
        return {
            "gini": {
                "baseline": impact.gini_baseline,
                "reform": impact.gini_reform,
                "change": impact.gini_change,
            },
            "top_10_percent_share": {
                "baseline": impact.top_10_percent_share_baseline,
                "reform": impact.top_10_percent_share_reform,
                "change": impact.top_10_percent_share_change,
            },
            "top_1_percent_share": {
                "baseline": impact.top_1_percent_share_baseline,
                "reform": impact.top_1_percent_share_reform,
                "change": impact.top_1_percent_share_change,
            }
        }
    
    def _get_budgetary_impact(self, report_id: str) -> dict:
        """Get budgetary impact for a report."""
        impact = self.session.query(BudgetaryImpact).filter_by(report_id=report_id).first()
        
        if not impact:
            return {}
        
        return {
            "budgetary_impact": impact.budgetary_impact,
            "tax_revenue_impact": impact.tax_revenue_impact,
            "state_tax_revenue_impact": impact.state_tax_revenue_impact,
            "benefit_spending_impact": impact.benefit_spending_impact,
            "households_affected": impact.households_affected,
            "baseline_net_income": impact.baseline_net_income,
        }
    
    def _get_labor_supply_impact(self, report_id: str) -> dict:
        """Get labor supply impact for a report."""
        impact = self.session.query(LaborSupplyImpact).filter_by(report_id=report_id).first()
        
        if not impact:
            return {}
        
        return {
            "substitution_effect": impact.substitution_effect,
            "income_effect": impact.income_effect,
            "total_change": impact.total_change,
            "revenue_change": impact.revenue_change,
            "hours": {
                "baseline": impact.hours_baseline,
                "reform": impact.hours_reform,
                "change": impact.hours_change,
                "income_effect": impact.hours_income_effect,
                "substitution_effect": impact.hours_substitution_effect,
            }
        }
    
    def _get_program_impacts(self, report_id: str) -> dict:
        """Get program-specific impacts for a report."""
        impacts = self.session.query(ProgramSpecificImpact).filter_by(report_id=report_id).all()
        
        result = {}
        for impact in impacts:
            result[impact.program_name] = {
                "baseline": impact.baseline_cost,
                "reform": impact.reform_cost,
                "difference": impact.cost_difference,
            }
        
        return result