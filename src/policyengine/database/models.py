"""SQLAlchemy models for PolicyEngine database."""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, 
    DateTime, JSON, ForeignKey, Enum, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
import importlib.metadata

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

def get_model_version(country: str) -> str:
    """Get the installed version of policyengine for a given country.
    
    Args:
        country: Country code (e.g., 'uk', 'us')
        
    Returns:
        Version string or None if package not found
    """
    try:
        package_name = f"policyengine-{country.lower()}"
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None

class SimulationStatus(enum.Enum):
    """Status of simulation processing."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User accounts for tracking who creates and modifies data."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True)
    
    # Authentication (optional - can integrate with external auth)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login = Column(DateTime, nullable=True)
    
    # API access (optional)
    api_key = Column(String, nullable=True, unique=True, index=True)
    api_key_created_at = Column(DateTime, nullable=True)
    
    # Additional metadata
    metadata_json = Column(JSON, nullable=True)  # For storing additional user data


# Metadata models only - actual data stored in .h5 files

class SimulationMetadata(Base):
    """Metadata for simulation stored in .h5 file. Can contain data for multiple years."""
    __tablename__ = "simulations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    country = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=True, index=True)  # Null for multi-year simulations
    
    # Storage information
    file_size_mb = Column(Float, nullable=True)
    
    # Foreign key references
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)
    model_version = Column(String, nullable=True)  # e.g., "0.5.2"
    
    # Processing metadata
    status = Column(Enum(SimulationStatus), default=SimulationStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    # Optional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags for filtering
    created_by = Column(String, ForeignKey("users.id"), nullable=True)  # User/system that created it
    
    # Relationships
    dataset = relationship("DatasetMetadata", backref="simulations")
    scenario = relationship("ScenarioMetadata", backref="simulations")
    
    def get_data(self, year: int = None):
        """Load the simulation data and return a ModelOutput object.
        
        Args:
            year: Optional year to retrieve. If None and only one year exists, returns that.
                 If None and multiple years exist, returns all years as dict.
        
        Returns:
            UKModelOutput/USModelOutput object for single year, or dict of {year: ModelOutput} for multiple years
        """
        if not hasattr(self, '_storage'):
            raise RuntimeError("SimulationMetadata was not loaded through Database.get_simulation()")
        
        # Import here to avoid circular imports
        from ..countries.uk import UKModelOutput
        from ..countries.us import USModelOutput
        
        # Load simulation data using storage backend
        data = self._storage.load_simulation(
            sim_id=self.id,
            country=self.country,
            scenario=self.scenario.name if self.scenario else None,
            dataset=self.dataset.name if self.dataset else None,
            year=None  # Year no longer relevant for file naming
        )
        
        if data is None:
            return None
        
        # Check if data has year structure
        if isinstance(data, dict) and all(isinstance(k, (int, str)) and str(k).isdigit() for k in data.keys()):
            # Data is organized by year
            years_available = list(data.keys())
            
            if year is not None:
                # Return specific year
                year_data = data.get(year) or data.get(str(year))
                if year_data is None:
                    raise ValueError(f"Year {year} not found in simulation data. Available years: {years_available}")
                
                # Convert to ModelOutput
                if self.country.lower() == 'uk':
                    return UKModelOutput.from_tables(year_data)
                elif self.country.lower() == 'us':
                    return USModelOutput.from_tables(year_data)
                else:
                    raise ValueError(f"Unsupported country: {self.country}")
            
            elif len(years_available) == 1:
                # Only one year available, return it
                year_data = data[years_available[0]]
                if self.country.lower() == 'uk':
                    return UKModelOutput.from_tables(year_data)
                elif self.country.lower() == 'us':
                    return USModelOutput.from_tables(year_data)
                else:
                    raise ValueError(f"Unsupported country: {self.country}")
            
            else:
                # Multiple years, return all as dict
                result = {}
                for yr, yr_data in data.items():
                    if self.country.lower() == 'uk':
                        result[yr] = UKModelOutput.from_tables(yr_data)
                    elif self.country.lower() == 'us':
                        result[yr] = USModelOutput.from_tables(yr_data)
                    else:
                        raise ValueError(f"Unsupported country: {self.country}")
                return result
        
        else:
            # Legacy format - single year data without year key
            if self.country.lower() == 'uk':
                return UKModelOutput.from_tables(data)
            elif self.country.lower() == 'us':
                return USModelOutput.from_tables(data)
            else:
                raise ValueError(f"Unsupported country: {self.country}")


class DatasetMetadata(Base):
    """Metadata for source datasets. e.g. 'EFRS 2023/24'"""
    __tablename__ = "datasets"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True, index=True)
    country = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=True, index=True)  # Nullable for multi-year datasets
    
    # Dataset characteristics
    source = Column(String, nullable=True)  # "FRS", "CPS", etc.
    version = Column(String, nullable=True)
    model_version = Column(String, nullable=True)  # e.g., "0.5.2"
    
    # File storage information (merged from DataFile)
    filename = Column(String, nullable=True)  # e.g., "cps_2023.h5"
    
    # Local storage
    local_path = Column(String, nullable=True)  # e.g., "./simulations/cps_2023.h5"
    
    # Google Cloud Storage
    gcs_bucket = Column(String, nullable=True)  # e.g., "policyengine-us-data"
    gcs_path = Column(String, nullable=True)  # e.g., "cps_2023.h5"
    
    # HuggingFace
    huggingface_repo = Column(String, nullable=True)  # e.g., "PolicyEngine/us-data"
    huggingface_path = Column(String, nullable=True)  # e.g., "cps_2023.h5"
    
    # File metadata
    file_size_mb = Column(Float, nullable=True)
    checksum = Column(String, nullable=True)  # For integrity checks
    
    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)


class ScenarioMetadata(Base):
    """Modifications made to baseline simulation behaviour."""
    __tablename__ = "scenarios"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False, index=True)
    model_version = Column(String, nullable=True)  # e.g., "0.5.2"
    
    # Parent scenario reference (usually current_law)
    parent_scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    parameter_changes = relationship("ParameterChangeMetadata", back_populates="scenario", cascade="all, delete-orphan")
    parent_scenario = relationship("ScenarioMetadata", remote_side=[id], backref="child_scenarios")
    
    # Unique constraint on (name, country) - same name allowed across countries
    __table_args__ = (
        UniqueConstraint('name', 'country', name='_scenario_name_country_uc'),
    )


class VariableMetadata(Base):
    """Registry of all variables that can be calculated."""
    __tablename__ = "variables"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)  # e.g., "household_net_income"
    country = Column(String, nullable=False, index=True)
    
    # Variable metadata
    label = Column(String, nullable=True)  # Human-readable name
    description = Column(Text, nullable=True)
    unit = Column(String, nullable=True)  # e.g., "GBP", "USD", "person", "boolean"
    value_type = Column(String, nullable=False)  # "float", "int", "bool", "string", "enum"
    entity = Column(String, nullable=False)  # "person", "household", "tax_unit", etc.
    definition_period = Column(String, nullable=True)  # "year", "month", "eternity"
    
    # Model version tracking
    model_version = Column(String, nullable=True)  # Version when this variable was added/updated
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Unique constraint on (name, country)
    __table_args__ = (
        UniqueConstraint('name', 'country', name='_variable_name_country_uc'),
    )


class ParameterMetadata(Base):
    """Registry of all parameters that can be modified."""
    __tablename__ = "parameters"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)  # e.g., "gov.basic_rate"
    country = Column(String, nullable=False, index=True)
    parent_id = Column(String, ForeignKey("parameters.id"), nullable=True)

    # Parameter metadata
    label = Column(String, nullable=True)  # Human-readable name
    description = Column(Text, nullable=True)
    unit = Column(String, nullable=True)  # e.g., "GBP", "percent", "boolean"
    data_type = Column(String, nullable=False)  # "float", "int", "bool", "string"
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    changes = relationship("ParameterChangeMetadata", back_populates="parameter", cascade="all, delete-orphan")


class ParameterChangeMetadata(Base):
    """Individual parameter change within a scenario."""
    __tablename__ = "parameter_changes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Foreign keys
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False, index=True)
    parameter_id = Column(String, ForeignKey("parameters.id"), nullable=False, index=True)
    
    # Time period for this change
    start_date = Column(DateTime, nullable=False, index=True)  # When this change takes effect
    end_date = Column(DateTime, nullable=True, index=True)  # When this change expires (null = indefinite)
    
    # The actual change
    value = Column(JSON, nullable=False)  # JSON to handle different data types
    
    # Ordering within scenario (for applying changes in sequence)
    order_index = Column(Integer, nullable=False, default=0)
    
    # Metadata
    model_version = Column(String, nullable=True)  # e.g., "0.5.2"
    description = Column(Text, nullable=True)  # Optional description of this specific change
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    scenario = relationship("ScenarioMetadata", back_populates="parameter_changes")
    parameter = relationship("ParameterMetadata", back_populates="changes")


# Report tables for storing economic impact results

class ReportMetadata(Base):
    """Metadata for economic impact report results."""
    __tablename__ = "reports"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=True, index=True)
    
    # References to simulations being compared
    baseline_simulation_id = Column(String, ForeignKey("simulations.id"), nullable=False)
    comparison_simulation_id = Column(String, ForeignKey("simulations.id"), nullable=False)
    
    # Processing metadata
    status = Column(Enum(SimulationStatus), default=SimulationStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    # Optional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    baseline_simulation = relationship("SimulationMetadata", foreign_keys=[baseline_simulation_id])
    comparison_simulation = relationship("SimulationMetadata", foreign_keys=[comparison_simulation_id])


# UK-specific report tables

class UKGovernmentBudget(Base):
    """UK government budget metrics."""
    __tablename__ = "report_uk_government_budget"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Overall budget
    gov_balance_baseline = Column(Float, nullable=True)
    gov_balance_reform = Column(Float, nullable=True)
    gov_balance_change = Column(Float, nullable=True)
    
    # Tax revenues
    gov_tax_baseline = Column(Float, nullable=True)
    gov_tax_reform = Column(Float, nullable=True)
    gov_tax_change = Column(Float, nullable=True)
    
    # Specific taxes
    income_tax_baseline = Column(Float, nullable=True)
    income_tax_reform = Column(Float, nullable=True)
    income_tax_change = Column(Float, nullable=True)
    
    national_insurance_baseline = Column(Float, nullable=True)
    national_insurance_reform = Column(Float, nullable=True)
    national_insurance_change = Column(Float, nullable=True)
    
    ni_employer_baseline = Column(Float, nullable=True)
    ni_employer_reform = Column(Float, nullable=True)
    ni_employer_change = Column(Float, nullable=True)
    
    vat_baseline = Column(Float, nullable=True)
    vat_reform = Column(Float, nullable=True)
    vat_change = Column(Float, nullable=True)
    
    capital_gains_tax_baseline = Column(Float, nullable=True)
    capital_gains_tax_reform = Column(Float, nullable=True)
    capital_gains_tax_change = Column(Float, nullable=True)
    
    # Government spending
    gov_spending_baseline = Column(Float, nullable=True)
    gov_spending_reform = Column(Float, nullable=True)
    gov_spending_change = Column(Float, nullable=True)
    
    # Specific benefits
    universal_credit_baseline = Column(Float, nullable=True)
    universal_credit_reform = Column(Float, nullable=True)
    universal_credit_change = Column(Float, nullable=True)
    
    state_pension_baseline = Column(Float, nullable=True)
    state_pension_reform = Column(Float, nullable=True)
    state_pension_change = Column(Float, nullable=True)
    
    pip_baseline = Column(Float, nullable=True)
    pip_reform = Column(Float, nullable=True)
    pip_change = Column(Float, nullable=True)
    
    dla_baseline = Column(Float, nullable=True)
    dla_reform = Column(Float, nullable=True)
    dla_change = Column(Float, nullable=True)
    
    housing_benefit_baseline = Column(Float, nullable=True)
    housing_benefit_reform = Column(Float, nullable=True)
    housing_benefit_change = Column(Float, nullable=True)
    
    working_tax_credit_baseline = Column(Float, nullable=True)
    working_tax_credit_reform = Column(Float, nullable=True)
    working_tax_credit_change = Column(Float, nullable=True)
    
    child_tax_credit_baseline = Column(Float, nullable=True)
    child_tax_credit_reform = Column(Float, nullable=True)
    child_tax_credit_change = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="uk_government_budget", uselist=False)


class UKHouseholdIncome(Base):
    """UK household income metrics."""
    __tablename__ = "report_uk_household_income"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Market income
    household_market_income_baseline = Column(Float, nullable=True)
    household_market_income_reform = Column(Float, nullable=True)
    household_market_income_change = Column(Float, nullable=True)
    
    # HBAI net income (official definition for poverty)
    hbai_household_net_income_baseline = Column(Float, nullable=True)
    hbai_household_net_income_reform = Column(Float, nullable=True)
    hbai_household_net_income_change = Column(Float, nullable=True)
    
    # Comprehensive net income
    household_net_income_baseline = Column(Float, nullable=True)
    household_net_income_reform = Column(Float, nullable=True)
    household_net_income_change = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="uk_household_income", uselist=False)


class UKDecileImpact(Base):
    """UK income/wealth/consumption decile impacts."""
    __tablename__ = "report_uk_decile_impacts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Decile grouping type
    decile_type = Column(String, nullable=False)  # 'equiv_hbai_household_net_income', 'consumption', 'total_wealth'
    decile = Column(Integer, nullable=False)  # 1-10, or 0 for all
    
    # Sum and mean metrics for each variable
    variable_name = Column(String, nullable=False)  # Name of variable being aggregated
    sum_baseline = Column(Float, nullable=True)
    sum_reform = Column(Float, nullable=True)
    sum_change = Column(Float, nullable=True)
    mean_baseline = Column(Float, nullable=True)
    mean_reform = Column(Float, nullable=True)
    mean_change = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="uk_decile_impacts")


class UKPovertyImpact(Base):
    """UK poverty rates (HBAI definitions)."""
    __tablename__ = "report_uk_poverty_impacts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Poverty type and demographic group
    poverty_type = Column(String, nullable=False)  # 'absolute_bhc', 'relative_bhc', 'absolute_ahc', 'relative_ahc'
    demographic_group = Column(String, nullable=False)  # 'all', 'child', 'working_age', 'pensioner'
    
    # Headcount and rate
    headcount_baseline = Column(Float, nullable=True)
    headcount_reform = Column(Float, nullable=True)
    headcount_change = Column(Float, nullable=True)
    
    rate_baseline = Column(Float, nullable=True)
    rate_reform = Column(Float, nullable=True)
    rate_change = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="uk_poverty_impacts")


class UKInequalityImpact(Base):
    """UK inequality metrics."""
    __tablename__ = "report_uk_inequality_impacts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Gini coefficient
    gini_baseline = Column(Float, nullable=True)
    gini_reform = Column(Float, nullable=True)
    gini_change = Column(Float, nullable=True)
    
    # Top income shares
    top_10_percent_share_baseline = Column(Float, nullable=True)
    top_10_percent_share_reform = Column(Float, nullable=True)
    top_10_percent_share_change = Column(Float, nullable=True)
    
    top_1_percent_share_baseline = Column(Float, nullable=True)
    top_1_percent_share_reform = Column(Float, nullable=True)
    top_1_percent_share_change = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="uk_inequality_impacts", uselist=False)


class UKWinnersLosers(Base):
    """UK winners and losers breakdown."""
    __tablename__ = "report_uk_winners_losers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Decile (1-10) or 0 for all
    decile = Column(Integer, nullable=False)
    
    # Share in each category
    gain_more_than_5_percent = Column(Float, nullable=True)
    gain_more_than_1_percent = Column(Float, nullable=True)
    no_change = Column(Float, nullable=True)
    lose_less_than_1_percent = Column(Float, nullable=True)
    lose_less_than_5_percent = Column(Float, nullable=True)
    lose_more_than_5_percent = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="uk_winners_losers")


# US-specific report tables

class USGovernmentBudget(Base):
    """US government budget metrics."""
    __tablename__ = "report_us_government_budget"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Federal tax revenues
    federal_tax_baseline = Column(Float, nullable=True)
    federal_tax_reform = Column(Float, nullable=True)
    federal_tax_change = Column(Float, nullable=True)
    
    # State tax revenues
    state_tax_baseline = Column(Float, nullable=True)
    state_tax_reform = Column(Float, nullable=True)
    state_tax_change = Column(Float, nullable=True)
    
    # Total tax revenues
    total_tax_baseline = Column(Float, nullable=True)
    total_tax_reform = Column(Float, nullable=True)
    total_tax_change = Column(Float, nullable=True)
    
    # Federal benefits
    federal_benefits_baseline = Column(Float, nullable=True)
    federal_benefits_reform = Column(Float, nullable=True)
    federal_benefits_change = Column(Float, nullable=True)
    
    # State benefits
    state_benefits_baseline = Column(Float, nullable=True)
    state_benefits_reform = Column(Float, nullable=True)
    state_benefits_change = Column(Float, nullable=True)
    
    # Total benefits
    total_benefits_baseline = Column(Float, nullable=True)
    total_benefits_reform = Column(Float, nullable=True)
    total_benefits_change = Column(Float, nullable=True)
    
    # Net budget impact
    net_impact = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="us_government_budget", uselist=False)


class USHouseholdIncome(Base):
    """US household income metrics."""
    __tablename__ = "report_us_household_income"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Market income
    household_market_income_baseline = Column(Float, nullable=True)
    household_market_income_reform = Column(Float, nullable=True)
    household_market_income_change = Column(Float, nullable=True)
    
    # Net income (after taxes and transfers)
    household_net_income_baseline = Column(Float, nullable=True)
    household_net_income_reform = Column(Float, nullable=True)
    household_net_income_change = Column(Float, nullable=True)
    
    # Net income including health benefits
    household_net_income_with_health_baseline = Column(Float, nullable=True)
    household_net_income_with_health_reform = Column(Float, nullable=True)
    household_net_income_with_health_change = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="us_household_income", uselist=False)


class USDecileImpact(Base):
    """US income decile impacts."""
    __tablename__ = "report_us_decile_impacts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Decile (1-10, or 0 for all)
    decile = Column(Integer, nullable=False)
    
    # Relative change in income
    relative_change = Column(Float, nullable=True)
    
    # Average dollar change
    average_change = Column(Float, nullable=True)
    
    # Share of total benefit
    share_of_benefit = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="us_decile_impacts")


class USPovertyImpact(Base):
    """US poverty impacts."""
    __tablename__ = "report_us_poverty_impacts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Poverty type (SPM, deep)
    poverty_type = Column(String, nullable=False)  # 'spm', 'deep'
    
    # Demographic group
    demographic_group = Column(String, nullable=False)  # 'all', 'child', 'adult', 'senior'
    
    # Headcount and rate
    headcount_baseline = Column(Float, nullable=True)
    headcount_reform = Column(Float, nullable=True)
    headcount_change = Column(Float, nullable=True)
    
    rate_baseline = Column(Float, nullable=True)
    rate_reform = Column(Float, nullable=True)
    rate_change = Column(Float, nullable=True)
    
    # Poverty gap (total dollars needed to lift out of poverty)
    gap_baseline = Column(Float, nullable=True)
    gap_reform = Column(Float, nullable=True)
    gap_change = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="us_poverty_impacts")


class USInequalityImpact(Base):
    """US inequality metrics."""
    __tablename__ = "report_us_inequality_impacts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Gini coefficient
    gini_baseline = Column(Float, nullable=True)
    gini_reform = Column(Float, nullable=True)
    gini_change = Column(Float, nullable=True)
    
    # Top income shares
    top_10_percent_share_baseline = Column(Float, nullable=True)
    top_10_percent_share_reform = Column(Float, nullable=True)
    top_10_percent_share_change = Column(Float, nullable=True)
    
    top_1_percent_share_baseline = Column(Float, nullable=True)
    top_1_percent_share_reform = Column(Float, nullable=True)
    top_1_percent_share_change = Column(Float, nullable=True)
    
    # Bottom 50% share
    bottom_50_percent_share_baseline = Column(Float, nullable=True)
    bottom_50_percent_share_reform = Column(Float, nullable=True)
    bottom_50_percent_share_change = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="us_inequality_impacts", uselist=False)


class USWinnersLosers(Base):
    """US winners and losers breakdown."""
    __tablename__ = "report_us_winners_losers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Decile (1-10) or 0 for all
    decile = Column(Integer, nullable=False)
    
    # Share in each category
    gain_more_than_5_percent = Column(Float, nullable=True)
    gain_more_than_1_percent = Column(Float, nullable=True)
    no_change = Column(Float, nullable=True)
    lose_less_than_1_percent = Column(Float, nullable=True)
    lose_less_than_5_percent = Column(Float, nullable=True)
    lose_more_than_5_percent = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="us_winners_losers")


class USProgramImpact(Base):
    """US program-specific impacts."""
    __tablename__ = "report_us_program_impacts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    
    # Program name
    program_name = Column(String, nullable=False)  # 'snap', 'tanf', 'eitc', 'ctc', 'social_security', etc.
    
    # Spending/cost
    baseline_cost = Column(Float, nullable=True)
    reform_cost = Column(Float, nullable=True)
    cost_change = Column(Float, nullable=True)
    
    # Recipients
    baseline_recipients = Column(Float, nullable=True)
    reform_recipients = Column(Float, nullable=True)
    recipients_change = Column(Float, nullable=True)
    
    # Average benefit per recipient
    baseline_average_benefit = Column(Float, nullable=True)
    reform_average_benefit = Column(Float, nullable=True)
    average_benefit_change = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    report = relationship("ReportMetadata", backref="us_program_impacts")
