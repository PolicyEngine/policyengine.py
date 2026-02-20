from policyengine.core import Output, OutputCollection
from policyengine.outputs.aggregate import Aggregate, AggregateType
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
from policyengine.outputs.local_authority_impact import (
    LocalAuthorityImpact,
    compute_uk_local_authority_impacts,
)
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)
from policyengine.outputs.inequality import (
    UK_INEQUALITY_INCOME_VARIABLE,
    US_INEQUALITY_INCOME_VARIABLE,
    Inequality,
    calculate_uk_inequality,
    calculate_us_inequality,
)
from policyengine.outputs.poverty import (
    UK_POVERTY_VARIABLES,
    US_POVERTY_VARIABLES,
    Poverty,
    UKPovertyType,
    USPovertyType,
    calculate_uk_poverty_rates,
    calculate_us_poverty_rates,
)

__all__ = [
    "Output",
    "OutputCollection",
    "Aggregate",
    "AggregateType",
    "ChangeAggregate",
    "ChangeAggregateType",
    "DecileImpact",
    "calculate_decile_impacts",
    "Poverty",
    "UKPovertyType",
    "USPovertyType",
    "UK_POVERTY_VARIABLES",
    "US_POVERTY_VARIABLES",
    "calculate_uk_poverty_rates",
    "calculate_us_poverty_rates",
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
]
