"""Pytest configuration and shared fixtures."""

# Import fixtures from fixtures module so pytest can discover them
from tests.fixtures.filtering_fixtures import (  # noqa: F401
    uk_test_dataset,
    us_test_dataset,
)
from tests.fixtures.parametric_reforms_fixtures import (  # noqa: F401
    mock_param_joint,
    mock_param_single,
    multi_period_param_values,
    multiple_different_params,
    param_value_with_end_date,
    single_param_value,
)
from tests.fixtures.region_fixtures import (  # noqa: F401
    empty_registry,
    sample_registry,
)
from tests.fixtures.us_reform_fixtures import (  # noqa: F401
    double_standard_deduction_policy,
    high_income_single_filer,
    married_couple_with_kids,
)
