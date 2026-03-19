from policyengine.core import Output, OutputCollection
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.outputs.analysis_strategy import (
    AnalysisStrategy,
    InequalityResult,
    PovertyResult,
    ProgramDefinition,
)
from policyengine.outputs.budget_summary import (
    BudgetSummaryItem,
    compute_budget_summary,
)
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType,
)
from policyengine.outputs.congressional_district_impact import (
    CongressionalDistrictImpact,
    compute_us_congressional_district_impacts,
)
from policyengine.outputs.constituency_impact import (
    ConstituencyImpact,
    compute_uk_constituency_impacts,
)
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
    compute_decile_impacts,
)
from policyengine.outputs.economic_impact import (
    economic_impact_analysis,
)
from policyengine.outputs.inequality import (
    UK_INEQUALITY_INCOME_VARIABLE,
    US_INEQUALITY_INCOME_VARIABLE,
    Inequality,
    calculate_uk_inequality,
    calculate_us_inequality,
)
from policyengine.outputs.intra_decile_impact import (
    IntraDecileImpact,
    compute_intra_decile_impacts,
)
from policyengine.outputs.local_authority_impact import (
    LocalAuthorityImpact,
    compute_uk_local_authority_impacts,
)
from policyengine.outputs.policy_reform_analysis import PolicyReformAnalysis
from policyengine.outputs.poverty import (
    AGE_GROUPS,
    GENDER_GROUPS,
    RACE_GROUPS,
    UK_POVERTY_VARIABLES,
    US_POVERTY_VARIABLES,
    Poverty,
    UKPovertyType,
    USPovertyType,
    calculate_uk_poverty_by_age,
    calculate_uk_poverty_by_gender,
    calculate_uk_poverty_rates,
    calculate_us_poverty_by_age,
    calculate_us_poverty_by_gender,
    calculate_us_poverty_by_race,
    calculate_us_poverty_rates,
)
from policyengine.outputs.program_statistics import compute_program_statistics

__all__ = [
    "Output",
    "OutputCollection",
    "Aggregate",
    "AggregateType",
    "ChangeAggregate",
    "ChangeAggregateType",
    "DecileImpact",
    "calculate_decile_impacts",
    "IntraDecileImpact",
    "compute_intra_decile_impacts",
    "Poverty",
    "UKPovertyType",
    "USPovertyType",
    "UK_POVERTY_VARIABLES",
    "US_POVERTY_VARIABLES",
    "calculate_uk_poverty_rates",
    "calculate_us_poverty_rates",
    "calculate_uk_poverty_by_age",
    "calculate_us_poverty_by_age",
    "calculate_uk_poverty_by_gender",
    "calculate_us_poverty_by_gender",
    "calculate_us_poverty_by_race",
    "AGE_GROUPS",
    "GENDER_GROUPS",
    "RACE_GROUPS",
    "Inequality",
    "UK_INEQUALITY_INCOME_VARIABLE",
    "US_INEQUALITY_INCOME_VARIABLE",
    "calculate_uk_inequality",
    "calculate_us_inequality",
    "CongressionalDistrictImpact",
    "compute_us_congressional_district_impacts",
    "ConstituencyImpact",
    "compute_uk_constituency_impacts",
    "LocalAuthorityImpact",
    "compute_uk_local_authority_impacts",
    "BudgetSummaryItem",
    "compute_budget_summary",
    "compute_decile_impacts",
    "compute_program_statistics",
    "PolicyReformAnalysis",
    "AnalysisStrategy",
    "ProgramDefinition",
    "PovertyResult",
    "InequalityResult",
    "economic_impact_analysis",
]
