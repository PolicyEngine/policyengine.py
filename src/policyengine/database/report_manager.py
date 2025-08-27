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
    UKGovernmentBudget,
    UKHouseholdIncome,
    UKDecileImpact,
    UKPovertyImpact,
    UKInequalityImpact,
    UKWinnersLosers,
)


class ReportManager:
    """Manages economic impact reports in the database."""
    
    def __init__(self, session: Session):
        """Initialise the report manager.
        
        Args:
            session: SimulationOrchestrator session
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
            Created or updated report metadata
        """
        # Check if report already exists with same name and country
        existing = self.session.query(ReportMetadata).filter_by(
            name=name,
            country=country
        ).first()
        
        if existing:
            # Delete old report impact data first
            print(f"Warning: Report '{name}' for country '{country}' already exists. Overwriting...")
            
            # Delete country-specific impact tables
            if country.lower() == "uk":
                self.session.query(UKGovernmentBudget).filter_by(report_id=existing.id).delete()
                self.session.query(UKHouseholdIncome).filter_by(report_id=existing.id).delete()
                self.session.query(UKDecileImpact).filter_by(report_id=existing.id).delete()
                self.session.query(UKPovertyImpact).filter_by(report_id=existing.id).delete()
                self.session.query(UKInequalityImpact).filter_by(report_id=existing.id).delete()
                self.session.query(UKWinnersLosers).filter_by(report_id=existing.id).delete()
            elif country.lower() == "us":
                # Import US tables
                from ..database.models import (
                    USGovernmentBudget,
                    USHouseholdIncome,
                    USDecileImpact,
                    USPovertyImpact,
                    USInequalityImpact,
                    USWinnersLosers,
                    USProgramImpact,
                )
                self.session.query(USGovernmentBudget).filter_by(report_id=existing.id).delete()
                self.session.query(USHouseholdIncome).filter_by(report_id=existing.id).delete()
                self.session.query(USDecileImpact).filter_by(report_id=existing.id).delete()
                self.session.query(USPovertyImpact).filter_by(report_id=existing.id).delete()
                self.session.query(USInequalityImpact).filter_by(report_id=existing.id).delete()
                self.session.query(USWinnersLosers).filter_by(report_id=existing.id).delete()
                self.session.query(USProgramImpact).filter_by(report_id=existing.id).delete()
            
            # Update existing report metadata
            existing.baseline_simulation_id = baseline_simulation_id
            existing.comparison_simulation_id = comparison_simulation_id
            existing.year = year
            existing.description = description or existing.description
            existing.tags = tags or existing.tags
            existing.updated_at = datetime.now()
            existing.status = SimulationStatus.PENDING
            report = existing
        else:
            # Create new report
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
        self.session.refresh(report)
        self.session.expunge(report)
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
        """Get report results including all impact data.
        
        Args:
            report_id: Report ID
            
        Returns:
            Dictionary containing report metadata and all impact results
        """
        # Get report metadata
        report = self.session.query(ReportMetadata).filter_by(id=report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Build base results
        results = {
            "report": {
                "id": report.id,
                "name": report.name,
                "country": report.country,
                "year": report.year,
                "baseline_simulation_id": report.baseline_simulation_id,
                "comparison_simulation_id": report.comparison_simulation_id,
                "description": report.description,
                "created_at": report.created_at.isoformat() if report.created_at else None,
            }
        }
        
        # Get country-specific impact results
        if report.country.lower() == "uk":
            # UK-specific tables
            government_budget = self.session.query(UKGovernmentBudget).filter_by(report_id=report_id).first()
            household_income = self.session.query(UKHouseholdIncome).filter_by(report_id=report_id).first()
            decile_impacts = self.session.query(UKDecileImpact).filter_by(report_id=report_id).all()
            poverty_impacts = self.session.query(UKPovertyImpact).filter_by(report_id=report_id).all()
            inequality_impact = self.session.query(UKInequalityImpact).filter_by(report_id=report_id).first()
            winners_losers = self.session.query(UKWinnersLosers).filter_by(report_id=report_id).all()
            
            results.update({
                "government_budget": {
                    "gov_balance": {
                        "baseline": government_budget.gov_balance_baseline if government_budget else None,
                        "reform": government_budget.gov_balance_reform if government_budget else None,
                        "change": government_budget.gov_balance_change if government_budget else None,
                    },
                    "gov_tax": {
                        "baseline": government_budget.gov_tax_baseline if government_budget else None,
                        "reform": government_budget.gov_tax_reform if government_budget else None,
                        "change": government_budget.gov_tax_change if government_budget else None,
                    },
                    "gov_spending": {
                        "baseline": government_budget.gov_spending_baseline if government_budget else None,
                        "reform": government_budget.gov_spending_reform if government_budget else None,
                        "change": government_budget.gov_spending_change if government_budget else None,
                    },
                } if government_budget else {},
                "household_income": {
                    "household_market_income": {
                        "baseline": household_income.household_market_income_baseline if household_income else None,
                        "reform": household_income.household_market_income_reform if household_income else None,
                        "change": household_income.household_market_income_change if household_income else None,
                    },
                    "hbai_household_net_income": {
                        "baseline": household_income.hbai_household_net_income_baseline if household_income else None,
                        "reform": household_income.hbai_household_net_income_reform if household_income else None,
                        "change": household_income.hbai_household_net_income_change if household_income else None,
                    },
                    "household_net_income": {
                        "baseline": household_income.household_net_income_baseline if household_income else None,
                        "reform": household_income.household_net_income_reform if household_income else None,
                        "change": household_income.household_net_income_change if household_income else None,
                    },
                } if household_income else {},
                "decile_impacts": [
                    {
                        "decile_type": impact.decile_type,
                        "decile": impact.decile,
                        "variable_name": impact.variable_name,
                        "sum_baseline": impact.sum_baseline,
                        "sum_reform": impact.sum_reform,
                        "sum_change": impact.sum_change,
                        "mean_baseline": impact.mean_baseline,
                        "mean_reform": impact.mean_reform,
                        "mean_change": impact.mean_change,
                    }
                    for impact in decile_impacts
                ],
                "poverty_impacts": [
                    {
                        "poverty_type": impact.poverty_type,
                        "demographic_group": impact.demographic_group,
                        "headcount_baseline": impact.headcount_baseline,
                        "headcount_reform": impact.headcount_reform,
                        "headcount_change": impact.headcount_change,
                        "rate_baseline": impact.rate_baseline,
                        "rate_reform": impact.rate_reform,
                        "rate_change": impact.rate_change,
                    }
                    for impact in poverty_impacts
                ],
                "inequality_impacts": {
                    "gini_baseline": inequality_impact.gini_baseline if inequality_impact else None,
                    "gini_reform": inequality_impact.gini_reform if inequality_impact else None,
                    "gini_change": inequality_impact.gini_change if inequality_impact else None,
                    "top_10_percent_share_baseline": inequality_impact.top_10_percent_share_baseline if inequality_impact else None,
                    "top_10_percent_share_reform": inequality_impact.top_10_percent_share_reform if inequality_impact else None,
                    "top_10_percent_share_change": inequality_impact.top_10_percent_share_change if inequality_impact else None,
                    "top_1_percent_share_baseline": inequality_impact.top_1_percent_share_baseline if inequality_impact else None,
                    "top_1_percent_share_reform": inequality_impact.top_1_percent_share_reform if inequality_impact else None,
                    "top_1_percent_share_change": inequality_impact.top_1_percent_share_change if inequality_impact else None,
                } if inequality_impact else {},
                "winners_losers": [
                    {
                        "decile": impact.decile,
                        "gain_more_than_5_percent": impact.gain_more_than_5_percent,
                        "gain_more_than_1_percent": impact.gain_more_than_1_percent,
                        "no_change": impact.no_change,
                        "lose_less_than_1_percent": impact.lose_less_than_1_percent,
                        "lose_less_than_5_percent": impact.lose_less_than_5_percent,
                        "lose_more_than_5_percent": impact.lose_more_than_5_percent,
                    }
                    for impact in winners_losers
                ],
            })
        elif report.country.lower() == "us":
            # US-specific tables
            # Import US tables
            from ..database.models import (
                USGovernmentBudget,
                USHouseholdIncome,
                USDecileImpact,
                USPovertyImpact,
                USInequalityImpact,
                USWinnersLosers,
                USProgramImpact,
            )
            
            government_budget = self.session.query(USGovernmentBudget).filter_by(report_id=report_id).first()
            household_income = self.session.query(USHouseholdIncome).filter_by(report_id=report_id).first()
            decile_impacts = self.session.query(USDecileImpact).filter_by(report_id=report_id).all()
            poverty_impacts = self.session.query(USPovertyImpact).filter_by(report_id=report_id).all()
            inequality_impact = self.session.query(USInequalityImpact).filter_by(report_id=report_id).first()
            winners_losers = self.session.query(USWinnersLosers).filter_by(report_id=report_id).all()
            program_impacts = self.session.query(USProgramImpact).filter_by(report_id=report_id).all()
            
            results.update({
                "government_budget": {
                    "federal_tax": {
                        "baseline": government_budget.federal_tax_baseline if government_budget else None,
                        "reform": government_budget.federal_tax_reform if government_budget else None,
                        "change": government_budget.federal_tax_change if government_budget else None,
                    },
                    "state_tax": {
                        "baseline": government_budget.state_tax_baseline if government_budget else None,
                        "reform": government_budget.state_tax_reform if government_budget else None,
                        "change": government_budget.state_tax_change if government_budget else None,
                    },
                    "total_tax": {
                        "baseline": government_budget.total_tax_baseline if government_budget else None,
                        "reform": government_budget.total_tax_reform if government_budget else None,
                        "change": government_budget.total_tax_change if government_budget else None,
                    },
                    "federal_benefits": {
                        "baseline": government_budget.federal_benefits_baseline if government_budget else None,
                        "reform": government_budget.federal_benefits_reform if government_budget else None,
                        "change": government_budget.federal_benefits_change if government_budget else None,
                    },
                    "state_benefits": {
                        "baseline": government_budget.state_benefits_baseline if government_budget else None,
                        "reform": government_budget.state_benefits_reform if government_budget else None,
                        "change": government_budget.state_benefits_change if government_budget else None,
                    },
                    "net_impact": government_budget.net_impact if government_budget else None,
                } if government_budget else {},
                "household_income": {
                    "household_market_income": {
                        "baseline": household_income.household_market_income_baseline if household_income else None,
                        "reform": household_income.household_market_income_reform if household_income else None,
                        "change": household_income.household_market_income_change if household_income else None,
                    },
                    "household_net_income": {
                        "baseline": household_income.household_net_income_baseline if household_income else None,
                        "reform": household_income.household_net_income_reform if household_income else None,
                        "change": household_income.household_net_income_change if household_income else None,
                    },
                    "household_net_income_with_health": {
                        "baseline": household_income.household_net_income_with_health_baseline if household_income else None,
                        "reform": household_income.household_net_income_with_health_reform if household_income else None,
                        "change": household_income.household_net_income_with_health_change if household_income else None,
                    },
                } if household_income else {},
                "decile_impacts": [
                    {
                        "decile": impact.decile,
                        "relative_change": impact.relative_change,
                        "average_change": impact.average_change,
                        "share_of_benefit": impact.share_of_benefit,
                    }
                    for impact in decile_impacts
                ],
                "poverty_impacts": [
                    {
                        "poverty_type": impact.poverty_type,
                        "demographic_group": impact.demographic_group,
                        "headcount_baseline": impact.headcount_baseline,
                        "headcount_reform": impact.headcount_reform,
                        "headcount_change": impact.headcount_change,
                        "rate_baseline": impact.rate_baseline,
                        "rate_reform": impact.rate_reform,
                        "rate_change": impact.rate_change,
                        "gap_baseline": impact.gap_baseline,
                        "gap_reform": impact.gap_reform,
                        "gap_change": impact.gap_change,
                    }
                    for impact in poverty_impacts
                ],
                "inequality_impacts": {
                    "gini_baseline": inequality_impact.gini_baseline if inequality_impact else None,
                    "gini_reform": inequality_impact.gini_reform if inequality_impact else None,
                    "gini_change": inequality_impact.gini_change if inequality_impact else None,
                    "top_10_percent_share_baseline": inequality_impact.top_10_percent_share_baseline if inequality_impact else None,
                    "top_10_percent_share_reform": inequality_impact.top_10_percent_share_reform if inequality_impact else None,
                    "top_10_percent_share_change": inequality_impact.top_10_percent_share_change if inequality_impact else None,
                    "top_1_percent_share_baseline": inequality_impact.top_1_percent_share_baseline if inequality_impact else None,
                    "top_1_percent_share_reform": inequality_impact.top_1_percent_share_reform if inequality_impact else None,
                    "top_1_percent_share_change": inequality_impact.top_1_percent_share_change if inequality_impact else None,
                    "bottom_50_percent_share_baseline": inequality_impact.bottom_50_percent_share_baseline if inequality_impact else None,
                    "bottom_50_percent_share_reform": inequality_impact.bottom_50_percent_share_reform if inequality_impact else None,
                    "bottom_50_percent_share_change": inequality_impact.bottom_50_percent_share_change if inequality_impact else None,
                } if inequality_impact else {},
                "winners_losers": [
                    {
                        "decile": impact.decile,
                        "gain_more_than_5_percent": impact.gain_more_than_5_percent,
                        "gain_more_than_1_percent": impact.gain_more_than_1_percent,
                        "no_change": impact.no_change,
                        "lose_less_than_1_percent": impact.lose_less_than_1_percent,
                        "lose_less_than_5_percent": impact.lose_less_than_5_percent,
                        "lose_more_than_5_percent": impact.lose_more_than_5_percent,
                    }
                    for impact in winners_losers
                ],
                "program_impacts": [
                    {
                        "program_name": impact.program_name,
                        "baseline_cost": impact.baseline_cost,
                        "reform_cost": impact.reform_cost,
                        "cost_change": impact.cost_change,
                        "baseline_recipients": impact.baseline_recipients,
                        "reform_recipients": impact.reform_recipients,
                        "recipients_change": impact.recipients_change,
                        "baseline_average_benefit": impact.baseline_average_benefit,
                        "reform_average_benefit": impact.reform_average_benefit,
                        "average_benefit_change": impact.average_benefit_change,
                    }
                    for impact in program_impacts
                ],
            })
        else:
            # Other countries not yet implemented
            results["error"] = f"Reports not yet implemented for country: {report.country}"
        
        return results