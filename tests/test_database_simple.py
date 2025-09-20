"""Test database model tables for simple set and get operations without complex relationships."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add src to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Define functions at module level to make them pickleable (not test_ prefix to avoid pytest)
def simulation_function(x):
    return x * 2


def policy_modifier_function(sim):
    sim.set_parameter("tax_rate", 0.25)
    return sim


def dynamic_modifier_function(sim):
    sim.set_parameter("benefit_amount", 1000)
    return sim


@pytest.fixture
def fresh_database():
    """Create a fresh database instance for each test."""
    # Import here to avoid circular imports
    from policyengine.database import Database

    # Use in-memory SQLite for testing
    db = Database(url="sqlite:///:memory:")
    db.create_tables()
    return db


def test_model_table_set_and_get(fresh_database):
    """Test ModelTable set and get operations."""
    from policyengine.models import Model

    model = Model(
        id="test_model_1",
        name="Test model",
        description="A test model",
        simulation_function=simulation_function,
    )

    # Set the model
    fresh_database.set(model)

    # Get the model
    retrieved_model = fresh_database.get(Model, id="test_model_1")

    assert retrieved_model is not None
    assert retrieved_model.id == "test_model_1"
    assert retrieved_model.name == "Test model"
    assert retrieved_model.description == "A test model"
    assert retrieved_model.simulation_function(5) == 10


def test_dataset_table_set_and_get(fresh_database):
    """Test DatasetTable set and get operations."""
    from policyengine.models import Dataset

    test_data = {"households": [{"id": 1, "income": 50000}]}

    dataset = Dataset(
        id="test_dataset_1",
        name="Test dataset",
        data=test_data,
    )

    fresh_database.set(dataset)
    retrieved = fresh_database.get(Dataset, id="test_dataset_1")

    assert retrieved is not None
    assert retrieved.id == "test_dataset_1"
    assert retrieved.name == "Test dataset"
    assert retrieved.data == test_data


def test_versioned_dataset_table_set_and_get(fresh_database):
    """Test VersionedDatasetTable set and get operations."""
    from policyengine.models import VersionedDataset

    versioned_dataset = VersionedDataset(
        id="test_versioned_1",
        name="Test versioned dataset",
        description="A test versioned dataset",
    )

    fresh_database.set(versioned_dataset)
    retrieved = fresh_database.get(VersionedDataset, id="test_versioned_1")

    assert retrieved is not None
    assert retrieved.id == "test_versioned_1"
    assert retrieved.name == "Test versioned dataset"
    assert retrieved.description == "A test versioned dataset"


def test_policy_table_set_and_get(fresh_database):
    """Test PolicyTable set and get operations."""
    from policyengine.models import Policy

    policy = Policy(
        id="test_policy_1",
        name="Test policy",
        description="A test policy",
        simulation_modifier=policy_modifier_function,
        created_at=datetime.now(),
    )

    fresh_database.set(policy)
    retrieved = fresh_database.get(Policy, id="test_policy_1")

    assert retrieved is not None
    assert retrieved.id == "test_policy_1"
    assert retrieved.name == "Test policy"
    assert retrieved.description == "A test policy"
    assert callable(retrieved.simulation_modifier)


def test_dynamic_table_set_and_get(fresh_database):
    """Test DynamicTable set and get operations."""
    from policyengine.models import Dynamic

    dynamic = Dynamic(
        id="test_dynamic_1",
        name="Test dynamic",
        description="A test dynamic policy",
        simulation_modifier=dynamic_modifier_function,
        created_at=datetime.now(),
    )

    fresh_database.set(dynamic)
    retrieved = fresh_database.get(Dynamic, id="test_dynamic_1")

    assert retrieved is not None
    assert retrieved.id == "test_dynamic_1"
    assert retrieved.name == "Test dynamic"
    assert retrieved.description == "A test dynamic policy"
    assert callable(retrieved.simulation_modifier)


def test_user_table_set_and_get(fresh_database):
    """Test UserTable set and get operations."""
    from policyengine.models import User

    user = User(
        id="test_user_1",
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        created_at=datetime.now(),
    )

    fresh_database.set(user)
    retrieved = fresh_database.get(User, id="test_user_1")

    assert retrieved is not None
    assert retrieved.id == "test_user_1"
    assert retrieved.username == "testuser"
    assert retrieved.email == "test@example.com"
    assert retrieved.first_name == "Test"
    assert retrieved.last_name == "User"


def test_report_table_set_and_get(fresh_database):
    """Test ReportTable set and get operations."""
    from policyengine.models import Report

    report = Report(
        id="test_report_1",
        label="Test Report",
        created_at=datetime.now(),
    )

    fresh_database.set(report)
    retrieved = fresh_database.get(Report, id="test_report_1")

    assert retrieved is not None
    assert retrieved.id == "test_report_1"
    assert retrieved.label == "Test Report"


def test_report_element_table_set_and_get(fresh_database):
    """Test ReportElementTable set and get operations."""
    from policyengine.models import ReportElement

    element = ReportElement(
        id="test_element_1",
        label="Test Element",
        type="chart",
        chart_type="bar",
    )

    fresh_database.set(element)
    retrieved = fresh_database.get(ReportElement, id="test_element_1")

    assert retrieved is not None
    assert retrieved.id == "test_element_1"
    assert retrieved.label == "Test Element"
    assert retrieved.type == "chart"
    assert retrieved.chart_type == "bar"


def test_multiple_operations_on_same_table(fresh_database):
    """Test multiple set and get operations on the same table."""
    from policyengine.models import Model

    # Create multiple model instances
    models = []
    for i in range(3):
        model = Model(
            id=f"model_{i}",
            name=f"Model {i}",
            description=f"Model number {i}",
            simulation_function=simulation_function,
        )
        models.append(model)
        fresh_database.set(model)

    # Retrieve all models
    for i, original in enumerate(models):
        retrieved = fresh_database.get(Model, id=f"model_{i}")
        assert retrieved is not None
        assert retrieved.id == original.id
        assert retrieved.name == original.name
        assert retrieved.description == original.description


def test_get_nonexistent_record(fresh_database):
    """Test getting a record that doesn't exist."""
    from policyengine.models import Model

    result = fresh_database.get(Model, id="nonexistent_id")
    assert result is None


def test_complex_data_compression(fresh_database):
    """Test that complex data types are properly compressed and decompressed."""
    from policyengine.models import Dataset

    # Create a dataset with complex nested structure
    complex_data = {
        "households": [
            {
                "id": i,
                "income": 30000 + i * 5000,
                "members": list(range(i + 1)),
            }
            for i in range(100)
        ],
        "metadata": {
            "source": "test",
            "year": 2024,
            "nested": {"deep": {"structure": True}},
        },
    }

    dataset = Dataset(
        id="complex_dataset",
        name="Complex dataset",
        data=complex_data,
    )

    fresh_database.set(dataset)
    retrieved = fresh_database.get(Dataset, id="complex_dataset")

    assert retrieved is not None
    assert retrieved.data == complex_data
    assert retrieved.data["households"][50]["income"] == 280000
    assert retrieved.data["metadata"]["nested"]["deep"]["structure"] is True
