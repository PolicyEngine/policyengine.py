"""Pytest configuration and shared fixtures."""

import pytest

# Import fixtures from fixtures module so pytest can discover them
from tests.fixtures.filtering_fixtures import (  # noqa: F401
    create_uk_test_dataset,
    create_us_test_dataset,
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

# Group (non-person) entities per country, and a helper to extract the
# entity_data dict a scoping strategy / filter operates on. Shared so the filter
# and region-group tests don't each redefine them.
US_GROUP_ENTITIES = ["household", "tax_unit", "spm_unit", "family", "marital_unit"]
UK_GROUP_ENTITIES = ["benunit", "household"]


def entity_data_of(dataset, group_entities):
    data = dataset.data
    return {entity: getattr(data, entity) for entity in ["person", *group_entities]}


@pytest.fixture
def us_group_entities():
    return list(US_GROUP_ENTITIES)


@pytest.fixture
def uk_group_entities():
    return list(UK_GROUP_ENTITIES)


@pytest.fixture
def us_entity_data():
    return entity_data_of(create_us_test_dataset(), US_GROUP_ENTITIES)


@pytest.fixture
def uk_entity_data():
    return entity_data_of(create_uk_test_dataset(), UK_GROUP_ENTITIES)
