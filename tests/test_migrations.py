"""Test migrations for updating database with tax-benefit model metadata and datasets."""

import pytest
from policyengine.database import Database
from policyengine.migrations import migrate_country, migrate_all
from policyengine.models import Parameter, Variable, Dataset


def test_migrate_uk_metadata():
    """Test that UK metadata can be migrated to an in-memory database."""
    # Skip if policyengine_uk is not installed
    pytest.importorskip("policyengine_uk")

    # Create in-memory database
    db = Database("sqlite:///:memory:")

    # Migrate UK metadata without datasets (faster)
    migrate_country(db, "uk", include_datasets=False)

    # Check that some variables were added
    variables = db.list(Variable)
    uk_variables = [v for v in variables if v.country == "uk"]
    assert len(uk_variables) > 0, "No UK variables were migrated"

    # Check that some parameters were added
    parameters = db.list(Parameter)
    uk_parameters = [p for p in parameters if p.country == "uk"]
    assert len(uk_parameters) > 0, "No UK parameters were migrated"

    # Check specific variable exists
    income_tax = db.get(Variable, name="income_tax", country="uk")
    assert income_tax is not None, "income_tax variable not found"
    assert income_tax.country == "uk"


def test_migrate_us_metadata():
    """Test that US metadata can be migrated to an in-memory database."""
    # Skip if policyengine_us is not installed
    pytest.importorskip("policyengine_us")

    # Create in-memory database
    db = Database("sqlite:///:memory:")

    # Migrate US metadata without datasets (faster)
    migrate_country(db, "us", include_datasets=False)

    # Check that some variables were added
    variables = db.list(Variable)
    us_variables = [v for v in variables if v.country == "us"]
    assert len(us_variables) > 0, "No US variables were migrated"

    # Check that some parameters were added
    parameters = db.list(Parameter)
    us_parameters = [p for p in parameters if p.country == "us"]
    assert len(us_parameters) > 0, "No US parameters were migrated"

    # Check specific variable exists
    federal_tax = db.get(Variable, name="income_tax", country="us")
    assert federal_tax is not None, "income_tax variable not found"
    assert federal_tax.country == "us"


def test_migrate_uk_dataset():
    """Test that UK datasets can be migrated to an in-memory database."""
    # Skip if policyengine_uk is not installed
    pytest.importorskip("policyengine_uk")

    # Create in-memory database
    db = Database("sqlite:///:memory:")

    # Migrate UK with datasets
    migrate_country(db, "uk", include_datasets=True)

    # Check that datasets were added
    datasets = db.list(Dataset)
    uk_datasets = [d for d in datasets if d.dataset_type.value == "uk"]
    assert len(uk_datasets) > 0, "No UK datasets were migrated"

    # Check for specific dataset patterns
    dataset_names = [d.name for d in uk_datasets]
    # Should have either enhanced_frs or frs datasets for multiple years
    assert any(
        "frs" in name for name in dataset_names
    ), "No FRS datasets found"


def test_migrate_us_dataset():
    """Test that US datasets can be migrated to an in-memory database."""
    # Skip if policyengine_us is not installed
    pytest.importorskip("policyengine_us")

    # Create in-memory database
    db = Database("sqlite:///:memory:")

    # Migrate US with datasets
    migrate_country(db, "us", include_datasets=True)

    # Check that datasets were added
    datasets = db.list(Dataset)
    us_datasets = [d for d in datasets if d.dataset_type.value == "us"]
    assert len(us_datasets) > 0, "No US datasets were migrated"

    # Check for specific dataset patterns
    dataset_names = [d.name for d in us_datasets]
    # Should have enhanced_cps datasets for multiple years
    assert any(
        "cps" in name for name in dataset_names
    ), "No CPS datasets found"


def test_migrate_all():
    """Test that all countries can be migrated together."""
    # Create in-memory database
    db = Database("sqlite:///:memory:")

    # Migrate all available countries (will skip if packages not installed)
    migrate_all(db, countries=["uk", "us"], include_datasets=False)

    # Check what was migrated
    variables = db.list(Variable)
    parameters = db.list(Parameter)

    # At least one country should have been migrated if any package is installed
    assert len(variables) > 0 or len(parameters) > 0, "No data was migrated"


def test_upsert_on_migration():
    """Test that migrations properly upsert data without duplicates."""
    # Skip if policyengine_uk is not installed
    pytest.importorskip("policyengine_uk")

    # Create in-memory database
    db = Database("sqlite:///:memory:")

    # First migration
    migrate_country(db, "uk", include_datasets=False)

    # Count initial items
    initial_variables = len(db.list(Variable))
    initial_parameters = len(db.list(Parameter))

    # Second migration (should upsert, not duplicate)
    migrate_country(db, "uk", include_datasets=False)

    # Count after second migration
    final_variables = len(db.list(Variable))
    final_parameters = len(db.list(Parameter))

    # Should be the same (no duplicates)
    assert final_variables == initial_variables, "Variables were duplicated"
    assert final_parameters == initial_parameters, "Parameters were duplicated"


def test_parameter_value_versioning():
    """Test that parameter values are properly versioned by model_version."""
    # Skip if policyengine_uk is not installed
    pytest.importorskip("policyengine_uk")

    # Create in-memory database
    db = Database("sqlite:///:memory:")

    # Migrate UK
    migrate_country(db, "uk", include_datasets=False)

    # Check that parameter values have model versions
    from policyengine.utils.version import get_model_version

    version = get_model_version("uk")

    # Query for a specific parameter's values
    from sqlmodel import select
    from policyengine.tables import ParameterValueTable

    with db.session() as s:
        stmt = (
            select(ParameterValueTable)
            .where(
                ParameterValueTable.country == "uk",
                ParameterValueTable.model_version == version,
            )
            .limit(10)
        )
        values = s.exec(stmt).all()

        assert (
            len(values) > 0
        ), f"No parameter values found for version {version}"
        for v in values:
            assert (
                v.model_version == version
            ), f"Wrong version: {v.model_version}"


def test_invalid_country():
    """Test that invalid country codes raise an error."""
    db = Database("sqlite:///:memory:")

    with pytest.raises(ValueError, match="Unknown country"):
        migrate_country(db, "invalid_country", include_datasets=False)
