"""Pure Pydantic data models for PolicyEngine calculations.

These models are independent of database concerns and can be used
for calculations without any database dependencies.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd


class SimulationDataModel(BaseModel):
    """Pure data model for simulation data."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # DataFrames for each entity
    person: pd.DataFrame
    household: pd.DataFrame
    
    # Optional DataFrames for different countries
    marital_unit: Optional[pd.DataFrame] = None
    family: Optional[pd.DataFrame] = None
    tax_unit: Optional[pd.DataFrame] = None
    spm_unit: Optional[pd.DataFrame] = None
    benefit_unit: Optional[pd.DataFrame] = None
    
    @property
    def table_names(self) -> List[str]:
        """Get list of available table names."""
        names = []
        for name in ["person", "household", "marital_unit", "family", "tax_unit", "spm_unit", "benefit_unit"]:
            if hasattr(self, name) and getattr(self, name) is not None:
                names.append(name)
        return names
    
    def get_tables(self) -> Dict[str, pd.DataFrame]:
        """Get all available tables as a dictionary."""
        return {
            name: getattr(self, name)
            for name in self.table_names
            if getattr(self, name) is not None
        }
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert to dictionary format for serialization."""
        tables = self.get_tables()
        return {
            name: {
                col: df[col].values.tolist()
                for col in df.columns
            }
            for name, df in tables.items()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationDataModel":
        """Create from dictionary representation."""
        tables = {}
        for name, table_data in data.items():
            if isinstance(table_data, pd.DataFrame):
                tables[name] = table_data
            elif isinstance(table_data, dict):
                tables[name] = pd.DataFrame(table_data)
            else:
                tables[name] = table_data
        
        # Ensure required fields exist
        if "person" not in tables:
            tables["person"] = pd.DataFrame()
        if "household" not in tables:
            tables["household"] = pd.DataFrame()
            
        return cls(**tables)


class ParameterChangeModel(BaseModel):
    """Pure data model for parameter changes."""
    parameter_name: str
    start_date: datetime
    end_date: Optional[datetime] = None
    value: Any
    description: Optional[str] = None
    order_index: int = 0


class ScenarioModel(BaseModel):
    """Pure data model for scenarios."""
    name: str
    country: str
    description: Optional[str] = None
    parameter_changes: List[ParameterChangeModel] = Field(default_factory=list)
    parent_scenario_name: Optional[str] = None
    model_version: Optional[str] = None


class DatasetModel(BaseModel):
    """Pure data model for datasets."""
    name: str
    country: str
    year: Optional[int] = None
    source: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    model_version: Optional[str] = None


class SimulationMetadataModel(BaseModel):
    """Pure data model for simulation metadata."""
    id: Optional[str] = None
    country: str
    year: Optional[int] = None
    dataset: DatasetModel
    scenario: ScenarioModel
    model_version: Optional[str] = None
    status: str = "pending"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ReportMetadataModel(BaseModel):
    """Pure data model for report metadata."""
    id: Optional[str] = None
    name: str
    country: str
    year: Optional[int] = None
    baseline_simulation_id: str
    comparison_simulation_id: str
    status: str = "pending"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


# Impact result models

class BudgetImpactModel(BaseModel):
    """Pure data model for budget impacts."""
    # Overall budget
    gov_balance_baseline: Optional[float] = None
    gov_balance_reform: Optional[float] = None
    gov_balance_change: Optional[float] = None
    
    # Tax revenues
    gov_tax_baseline: Optional[float] = None
    gov_tax_reform: Optional[float] = None
    gov_tax_change: Optional[float] = None
    
    # Government spending
    gov_spending_baseline: Optional[float] = None
    gov_spending_reform: Optional[float] = None
    gov_spending_change: Optional[float] = None
    
    # Additional fields can be added dynamically
    additional_metrics: Dict[str, Dict[str, float]] = Field(default_factory=dict)


class HouseholdIncomeImpactModel(BaseModel):
    """Pure data model for household income impacts."""
    household_market_income_baseline: Optional[float] = None
    household_market_income_reform: Optional[float] = None
    household_market_income_change: Optional[float] = None
    
    household_net_income_baseline: Optional[float] = None
    household_net_income_reform: Optional[float] = None
    household_net_income_change: Optional[float] = None
    
    # Additional income metrics
    additional_metrics: Dict[str, Dict[str, float]] = Field(default_factory=dict)


class DecileImpactModel(BaseModel):
    """Pure data model for decile impacts."""
    decile: int
    decile_type: str  # 'income', 'wealth', 'consumption'
    
    relative_change: float
    average_change: float
    share_of_benefit: Optional[float] = None
    
    # Winners and losers breakdown
    gain_more_than_5_percent: Optional[float] = None
    gain_more_than_1_percent: Optional[float] = None
    no_change: Optional[float] = None
    lose_less_than_1_percent: Optional[float] = None
    lose_less_than_5_percent: Optional[float] = None
    lose_more_than_5_percent: Optional[float] = None


class PovertyImpactModel(BaseModel):
    """Pure data model for poverty impacts."""
    poverty_type: str  # 'absolute', 'relative', 'spm', 'deep'
    demographic_group: str  # 'all', 'child', 'adult', 'senior'
    
    headcount_baseline: Optional[float] = None
    headcount_reform: Optional[float] = None
    headcount_change: Optional[float] = None
    
    rate_baseline: Optional[float] = None
    rate_reform: Optional[float] = None
    rate_change: Optional[float] = None
    
    gap_baseline: Optional[float] = None
    gap_reform: Optional[float] = None
    gap_change: Optional[float] = None


class InequalityImpactModel(BaseModel):
    """Pure data model for inequality impacts."""
    gini_baseline: Optional[float] = None
    gini_reform: Optional[float] = None
    gini_change: Optional[float] = None
    
    top_10_percent_share_baseline: Optional[float] = None
    top_10_percent_share_reform: Optional[float] = None
    top_10_percent_share_change: Optional[float] = None
    
    top_1_percent_share_baseline: Optional[float] = None
    top_1_percent_share_reform: Optional[float] = None
    top_1_percent_share_change: Optional[float] = None
    
    bottom_50_percent_share_baseline: Optional[float] = None
    bottom_50_percent_share_reform: Optional[float] = None
    bottom_50_percent_share_change: Optional[float] = None


class EconomicImpactModel(BaseModel):
    """Complete economic impact results."""
    report_metadata: ReportMetadataModel
    budget_impact: Optional[BudgetImpactModel] = None
    household_income: Optional[HouseholdIncomeImpactModel] = None
    decile_impacts: List[DecileImpactModel] = Field(default_factory=list)
    poverty_impacts: List[PovertyImpactModel] = Field(default_factory=list)
    inequality_impact: Optional[InequalityImpactModel] = None