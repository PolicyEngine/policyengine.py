"""Test the POLICYENGINE_DB constant and database connection."""

import pytest
from policyengine.database import Database, POLICYENGINE_DB


def test_policyengine_db_constant():
    """Test that POLICYENGINE_DB constant is defined and has the correct value."""
    assert POLICYENGINE_DB == "policyengine"


def test_database_with_constant_no_password():
    """Test that using POLICYENGINE_DB without password raises error."""
    import os

    # Make sure password is not set
    old_password = os.environ.pop("POLICYENGINE_DB_PASSWORD", None)

    try:
        with pytest.raises(ValueError, match="POLICYENGINE_DB_PASSWORD"):
            db = Database(POLICYENGINE_DB)
    finally:
        # Restore password if it was set
        if old_password:
            os.environ["POLICYENGINE_DB_PASSWORD"] = old_password


def test_database_with_memory():
    """Test that regular database creation still works."""
    db = Database("sqlite:///:memory:")
    assert db is not None
    assert db.engine is not None


def test_database_import_from_main_package():
    """Test that Database and POLICYENGINE_DB can be imported from main package."""
    from policyengine import Database as DB2, POLICYENGINE_DB as PDB2

    assert DB2 == Database
    assert PDB2 == POLICYENGINE_DB
    assert PDB2 == "policyengine"
