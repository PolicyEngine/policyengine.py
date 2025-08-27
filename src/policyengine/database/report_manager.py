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