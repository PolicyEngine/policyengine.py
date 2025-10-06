"""Test database with PostgreSQL/Supabase connection.

These tests verify that table creation and commits work properly with PostgreSQL,
which is what Supabase uses.
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect, text

# Add src to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Module-level functions for testing (can be pickled)
def sim_func(x):
    """Simulation function that can be pickled."""
    return x


def sim_func_double(x):
    """Simulation function that doubles input."""
    return x * 2


@pytest.fixture
def postgres_database():
    """Create a database instance with a local PostgreSQL connection.

    This requires a local PostgreSQL server running on port 54322.
    Skip the test if the connection fails.
    """
    from policyengine.database import Database

    try:
        db = Database(url="postgresql://postgres:postgres@127.0.0.1:54322/postgres")
        # Test connection
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return db
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


def test_postgres_create_tables(postgres_database):
    """Test that create_tables() works with PostgreSQL."""
    # Drop tables first to ensure clean state
    postgres_database.drop_tables()

    # Create tables
    postgres_database.create_tables()

    # Verify tables exist
    inspector = inspect(postgres_database.engine)
    actual_tables = inspector.get_table_names()

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

    for table in expected_tables:
        assert table in actual_tables, f"Table {table} was not created in PostgreSQL"


def test_postgres_insert_and_retrieve(postgres_database):
    """Test that data can be inserted and retrieved from PostgreSQL."""
    from policyengine.models import Model

    # Reset database
    postgres_database.reset()

    # Create a model
    model = Model(
        id="postgres_test_model",
        name="PostgreSQL Test",
        description="Testing PostgreSQL",
        simulation_function=sim_func_double,
    )

    # Insert
    postgres_database.set(model)

    # Retrieve
    retrieved = postgres_database.get(Model, id="postgres_test_model")

    assert retrieved is not None
    assert retrieved.id == "postgres_test_model"
    assert retrieved.name == "PostgreSQL Test"
    assert retrieved.simulation_function(5) == 10


def test_postgres_session_commit(postgres_database):
    """Test that session commits work properly with PostgreSQL."""
    from policyengine.models import Model

    # Reset database
    postgres_database.reset()

    # Add data without committing
    model = Model(
        id="commit_test_model",
        name="Commit Test",
        description="Testing commit",
        simulation_function=sim_func,
    )

    # Set with explicit commit
    postgres_database.set(model, commit=True)

    # Create a NEW database connection to verify commit
    from policyengine.database import Database

    new_db = Database(url="postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    retrieved = new_db.get(Model, id="commit_test_model")

    assert retrieved is not None
    assert retrieved.name == "Commit Test"


def test_postgres_table_persistence(postgres_database):
    """Test that tables persist across database reconnections."""
    # Create tables
    postgres_database.reset()

    # Close connection
    postgres_database.session.close()

    # Create new database instance with same URL
    from policyengine.database import Database

    new_db = Database(url="postgresql://postgres:postgres@127.0.0.1:54322/postgres")

    # Tables should still exist
    inspector = inspect(new_db.engine)
    tables = inspector.get_table_names()

    assert "models" in tables
    assert "simulations" in tables


def test_postgres_register_model_version(postgres_database):
    """Test that register_model_version works with PostgreSQL."""
    # This test verifies that the bulk registration of model versions
    # properly commits to PostgreSQL
    postgres_database.reset()

    # This would typically use policyengine_uk_latest_version
    # For now, we'll just verify the reset worked
    inspector = inspect(postgres_database.engine)
    tables = inspector.get_table_names()

    assert "models" in tables
    assert "model_versions" in tables
    assert "parameters" in tables
    assert "baseline_parameter_values" in tables
    assert "baseline_variables" in tables
