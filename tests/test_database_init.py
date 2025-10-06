"""Test database initialization and table creation."""

import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect

# Add src to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Module-level functions for testing (can be pickled)
# Note: Don't use test_ prefix or pytest will try to run them
def sim_func(x):
    """Simulation function that can be pickled."""
    return x


def sim_func_double(x):
    """Simulation function that doubles input."""
    return x * 2


@pytest.fixture
def fresh_database():
    """Create a fresh database instance for each test."""
    from policyengine.database import Database

    # Use in-memory SQLite for testing
    db = Database(url="sqlite:///:memory:")
    return db


def test_database_creates_engine(fresh_database):
    """Test that database initialization creates an engine."""
    assert fresh_database.engine is not None
    assert fresh_database.url == "sqlite:///:memory:"


def test_database_creates_session(fresh_database):
    """Test that database initialization creates a session."""
    assert fresh_database.session is not None


def test_create_tables_creates_all_registered_tables(fresh_database):
    """Test that create_tables() creates all registered tables."""
    fresh_database.create_tables()

    # Get inspector to check actual database tables
    inspector = inspect(fresh_database.engine)
    actual_tables = inspector.get_table_names()

    # Expected tables based on registered table links
    expected_tables = {
        "models",
        "model_versions",
        "datasets",
        "versioned_datasets",
        "policies",
        "dynamics",
        "parameters",
        "parameter_values",
        "baseline_parameter_values",
        "baseline_variables",
        "simulations",
        "aggregates",
    }

    # Check that all expected tables exist
    for table in expected_tables:
        assert table in actual_tables, f"Table {table} was not created"


def test_register_table_creates_table(fresh_database):
    """Test that register_table registers the table link."""
    # Tables should be registered but NOT created until create_tables() is called
    inspector = inspect(fresh_database.engine)
    initial_tables = set(inspector.get_table_names())

    # No tables should exist yet
    assert len(initial_tables) == 0

    # But table links should be registered
    assert len(fresh_database._model_table_links) == 12

    # After calling create_tables(), tables should exist
    fresh_database.create_tables()
    inspector = inspect(fresh_database.engine)
    tables_after = set(inspector.get_table_names())
    assert "models" in tables_after


def test_reset_drops_and_recreates_tables(fresh_database):
    """Test that reset() drops and recreates all tables."""
    from policyengine.models import Model

    # Create tables first
    fresh_database.create_tables()

    # Add some data
    model = Model(
        id="test_model",
        name="Test",
        description="Test model",
        simulation_function=sim_func,
    )
    fresh_database.set(model)

    # Verify data exists
    retrieved = fresh_database.get(Model, id="test_model")
    assert retrieved is not None

    # Reset the database
    fresh_database.reset()

    # Tables should exist but be empty
    inspector = inspect(fresh_database.engine)
    tables = inspector.get_table_names()
    assert "models" in tables

    # Data should be gone
    retrieved_after_reset = fresh_database.get(Model, id="test_model")
    assert retrieved_after_reset is None


def test_drop_tables_removes_all_tables(fresh_database):
    """Test that drop_tables() removes all tables."""
    # Create tables first
    fresh_database.create_tables()

    # Verify tables exist
    inspector = inspect(fresh_database.engine)
    tables_before = inspector.get_table_names()
    assert len(tables_before) > 0

    # Drop tables
    fresh_database.drop_tables()

    # Verify tables are gone
    inspector = inspect(fresh_database.engine)
    tables_after = inspector.get_table_names()
    assert len(tables_after) == 0


def test_context_manager_commits_on_success():
    """Test that context manager commits on successful operations."""
    from policyengine.database import Database
    from policyengine.models import Model

    db = Database(url="sqlite:///:memory:")
    db.create_tables()

    # Use context manager to add data
    with db as session:
        model = Model(
            id="test_context_model",
            name="Context Test",
            description="Testing context manager",
            simulation_function=sim_func,
        )
        db.set(model, commit=False)  # Don't commit inside set

    # Data should be committed after context exit
    retrieved = db.get(Model, id="test_context_model")
    assert retrieved is not None
    assert retrieved.name == "Context Test"


def test_context_manager_rolls_back_on_error():
    """Test that context manager rolls back on errors."""
    from policyengine.database import Database
    from policyengine.models import Model

    db = Database(url="sqlite:///:memory:")
    db.create_tables()

    # Try to use context manager with an error
    try:
        with db as session:
            model = Model(
                id="test_rollback_model",
                name="Rollback Test",
                description="Testing rollback",
                simulation_function=sim_func,
            )
            db.set(model, commit=False)
            # Raise an error to trigger rollback
            raise ValueError("Test error")
    except ValueError:
        pass

    # Data should NOT be in database due to rollback
    retrieved = db.get(Model, id="test_rollback_model")
    assert retrieved is None


def test_database_url_variations():
    """Test that database works with different URL formats."""
    from policyengine.database import Database

    # Test in-memory SQLite
    db1 = Database(url="sqlite:///:memory:")
    assert db1.engine is not None

    # Test file-based SQLite
    db2 = Database(url="sqlite:///test.db")
    assert db2.engine is not None


def test_all_table_links_registered(fresh_database):
    """Test that all expected table links are registered."""
    expected_count = 12  # Based on the number of table links in __init__
    assert len(fresh_database._model_table_links) == expected_count

    # Verify specific table links exist
    from policyengine.models import (
        Aggregate,
        Dataset,
        Dynamic,
        Model,
        ModelVersion,
        Parameter,
        Policy,
        Simulation,
        VersionedDataset,
    )

    model_classes = [link.model_cls for link in fresh_database._model_table_links]

    assert Model in model_classes
    assert ModelVersion in model_classes
    assert Dataset in model_classes
    assert VersionedDataset in model_classes
    assert Policy in model_classes
    assert Dynamic in model_classes
    assert Parameter in model_classes
    assert Simulation in model_classes
    assert Aggregate in model_classes


def test_verify_tables_exist(fresh_database):
    """Test the verify_tables_exist method."""
    # Before creating tables
    results_before = fresh_database.verify_tables_exist()
    # Some tables may exist from register_table calls during __init__
    # So we just check the method runs

    # After creating tables
    fresh_database.create_tables()
    results_after = fresh_database.verify_tables_exist()

    # All tables should exist now
    assert all(results_after.values()), f"Some tables don't exist: {results_after}"

    # Check specific tables
    assert results_after.get("models") is True
    assert results_after.get("simulations") is True
    assert results_after.get("parameters") is True
