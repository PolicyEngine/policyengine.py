"""UK-specific economic impact report using pure data models.

This refactored version shows how to use the new architecture that separates
database concerns from calculation logic.
"""

from typing import Optional
from sqlalchemy.orm import Session

from .model_output import UKModelOutput
from ...data_models import (
    SimulationDataModel,
    ReportMetadataModel,
    EconomicImpactModel,
)
from ...calculations import calculate_economic_impacts
from ...adapters import (
    save_economic_impact_to_db,
    report_metadata_orm_to_pydantic,
)
from ...database.models import ReportMetadata


class UKEconomicImpactReportRefactored:
    """UK-specific economic impact report using pure data models.
    
    This class demonstrates the refactored approach where:
    1. Calculations work with pure Pydantic models
    2. Database operations are handled separately through adapters
    3. The report class acts as a coordinator
    """
    
    def __init__(self, session: Optional[Session] = None):
        """Initialise UK economic impact report.
        
        Args:
            session: Optional database session. If not provided, results
                    won't be persisted to database.
        """
        self.session = session
    
    def calculate_impacts(
        self,
        baseline: UKModelOutput,
        comparison: UKModelOutput,
        report_name: str = "UK Economic Impact Report",
        report_id: Optional[str] = None,
    ) -> EconomicImpactModel:
        """Calculate all economic impacts using pure data models.
        
        This method works without any database dependencies.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison/reform simulation output
            report_name: Name for the report
            report_id: Optional report ID
            
        Returns:
            EconomicImpactModel with all calculated impacts
        """
        # Create report metadata
        report_metadata = ReportMetadataModel(
            id=report_id,
            name=report_name,
            country="uk",
            baseline_simulation_id="baseline",  # These would be real IDs in practice
            comparison_simulation_id="comparison",
        )
        
        # Since UKModelOutput now extends SimulationDataModel,
        # we can use them directly with the calculation functions
        impacts = calculate_economic_impacts(
            baseline=baseline,
            comparison=comparison,
            report_metadata=report_metadata
        )
        
        return impacts
    
    def calculate_and_save_impacts(
        self,
        baseline: UKModelOutput,
        comparison: UKModelOutput,
        report: ReportMetadata,
    ) -> EconomicImpactModel:
        """Calculate impacts and save to database.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison/reform simulation output
            report: Report metadata from database
            
        Returns:
            EconomicImpactModel with all calculated impacts
        """
        if not self.session:
            raise ValueError("Database session required for saving impacts")
        
        # Convert ORM model to Pydantic
        report_metadata = report_metadata_orm_to_pydantic(report)
        
        # Calculate impacts using pure models
        impacts = calculate_economic_impacts(
            baseline=baseline,
            comparison=comparison,
            report_metadata=report_metadata
        )
        
        # Save to database using adapter
        save_economic_impact_to_db(self.session, impacts)
        
        return impacts
    
    @classmethod
    def calculate_without_database(
        cls,
        baseline: UKModelOutput,
        comparison: UKModelOutput,
        report_name: str = "UK Economic Impact Report"
    ) -> EconomicImpactModel:
        """Static method to calculate impacts without any database dependency.
        
        This demonstrates that calculations can work completely independently
        of database concerns.
        
        Args:
            baseline: Baseline simulation output
            comparison: Comparison/reform simulation output
            report_name: Name for the report
            
        Returns:
            EconomicImpactModel with all calculated impacts
        """
        report_metadata = ReportMetadataModel(
            name=report_name,
            country="uk",
            baseline_simulation_id="baseline",
            comparison_simulation_id="comparison",
        )
        
        return calculate_economic_impacts(
            baseline=baseline,
            comparison=comparison,
            report_metadata=report_metadata
        )


# Example usage functions

def example_pure_calculation():
    """Example of using calculations without database."""
    import pandas as pd
    
    # Create sample data
    sample_household = pd.DataFrame({
        "household_net_income": [30000, 45000, 25000, 60000, 35000],
        "household_weight": [1.2, 0.8, 1.5, 0.9, 1.1],
        "household_count_people": [2, 3, 1, 4, 2],
        "household_tax": [5000, 8000, 3000, 12000, 6000],
        "household_benefits": [2000, 1000, 3000, 500, 1500],
    })
    
    sample_person = pd.DataFrame({
        "person_weight": [1.2, 1.2, 0.8, 0.8, 0.8, 1.5, 0.9, 0.9, 0.9, 0.9, 1.1, 1.1],
        "age": [35, 33, 42, 40, 12, 28, 55, 52, 18, 15, 38, 10],
        "is_male": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        "in_poverty": [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    })
    
    # Create baseline output
    baseline = UKModelOutput(
        person=sample_person,
        household=sample_household,
        benefit_unit=pd.DataFrame(),  # Empty for this example
    )
    
    # Create comparison with some changes
    comparison_household = sample_household.copy()
    comparison_household["household_net_income"] *= 1.02  # 2% increase
    comparison_household["household_tax"] *= 0.95  # 5% tax reduction
    
    comparison_person = sample_person.copy()
    comparison_person["in_poverty"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # Lifted one out of poverty
    
    comparison = UKModelOutput(
        person=comparison_person,
        household=comparison_household,
        benefit_unit=pd.DataFrame(),
    )
    
    # Calculate impacts without any database
    impacts = UKEconomicImpactReportRefactored.calculate_without_database(
        baseline=baseline,
        comparison=comparison,
        report_name="Example Tax Reform Impact"
    )
    
    # Access results as pure Python objects
    print(f"Budget impact: £{impacts.budget_impact.gov_tax_change:,.2f}")
    print(f"Gini change: {impacts.inequality_impact.gini_change:.4f}")
    for decile_impact in impacts.decile_impacts:
        print(f"Decile {decile_impact.decile}: {decile_impact.relative_change:.2%} change")
    
    return impacts