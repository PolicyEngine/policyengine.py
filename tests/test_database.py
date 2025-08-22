"""Tests for PolicyEngine database."""

import pytest
import tempfile
import os
from policyengine import (
    Database,
    DatabaseConfig,
    Population,
    Scenario,
    SingleYearDataset,
    EntityTable,
    UKPerson,
    UKHousehold,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    config = DatabaseConfig(
        connection_string=f"sqlite:///{db_path}"
    )
    db = Database(config)
    
    yield db
    
    # Cleanup
    os.unlink(db_path)


class TestDatabase:
    def test_database_creation(self, temp_db):
        assert temp_db is not None
        stats = temp_db.get_statistics()
        assert stats["populations"] == 0
        assert stats["scenarios"] == 0
        assert stats["datasets"] == 0
    
    def test_save_and_get_population(self, temp_db):
        pop = Population(name="Test Pop", country="uk", year=2024)
        pop.add_entity_count("Person", 1000)
        
        pop_id = temp_db.save_population(pop)
        assert pop_id == pop.id
        
        retrieved = temp_db.get_population(pop_id)
        assert retrieved is not None
        assert retrieved.name == "Test Pop"
        assert retrieved.country == "uk"
        assert retrieved.year == 2024
        assert retrieved.entity_counts["Person"] == 1000
    
    def test_list_populations(self, temp_db):
        pop1 = Population(name="UK 2024", country="uk", year=2024)
        pop2 = Population(name="UK 2025", country="uk", year=2025)
        pop3 = Population(name="US 2024", country="us", year=2024)
        
        temp_db.save_population(pop1)
        temp_db.save_population(pop2)
        temp_db.save_population(pop3)
        
        # List all
        all_pops = temp_db.list_populations()
        assert len(all_pops) == 3
        
        # Filter by country
        uk_pops = temp_db.list_populations(country="uk")
        assert len(uk_pops) == 2
        
        # Filter by year
        pops_2024 = temp_db.list_populations(year=2024)
        assert len(pops_2024) == 2
        
        # Filter by both
        uk_2024 = temp_db.list_populations(country="uk", year=2024)
        assert len(uk_2024) == 1
        assert uk_2024[0].name == "UK 2024"
    
    def test_delete_population(self, temp_db):
        pop = Population(name="Test", country="uk", year=2024)
        pop_id = temp_db.save_population(pop)
        
        assert temp_db.get_population(pop_id) is not None
        assert temp_db.delete_population(pop_id) is True
        assert temp_db.get_population(pop_id) is None
        assert temp_db.delete_population(pop_id) is False
    
    def test_save_and_get_scenario(self, temp_db):
        scenario = Scenario(name="Test Scenario", country="uk")
        scenario.add_reform("tax.rate", 0.25, "2024")
        
        scenario_id = temp_db.save_scenario(scenario)
        assert scenario_id == scenario.id
        
        retrieved = temp_db.get_scenario(scenario_id)
        assert retrieved is not None
        assert retrieved.name == "Test Scenario"
        assert retrieved.country == "uk"
        assert len(retrieved.reforms) == 1
    
    def test_list_scenarios(self, temp_db):
        s1 = Scenario(name="UK Reform", country="uk")
        s2 = Scenario(name="UK Baseline", country="uk", baseline=True)
        s3 = Scenario(name="US Reform", country="us")
        
        temp_db.save_scenario(s1)
        temp_db.save_scenario(s2)
        temp_db.save_scenario(s3)
        
        # List all
        all_scenarios = temp_db.list_scenarios()
        assert len(all_scenarios) == 3
        
        # Filter by country
        uk_scenarios = temp_db.list_scenarios(country="uk")
        assert len(uk_scenarios) == 2
        
        # Filter baseline only
        baselines = temp_db.list_scenarios(baseline_only=True)
        assert len(baselines) == 1
        assert baselines[0].name == "UK Baseline"
    
    def test_save_and_get_dataset(self, temp_db):
        dataset = SingleYearDataset(year=2024, country="uk")
        
        persons = EntityTable(entity_type=UKPerson)
        persons.add_entity(UKPerson(
            id="p1", age=30, benunit_id="b1", household_id="h1"
        ))
        dataset.add_table("persons", persons)
        
        dataset_id = temp_db.save_dataset(dataset)
        assert dataset_id is not None
        
        retrieved = temp_db.get_dataset(dataset_id=dataset_id)
        assert retrieved is not None
        assert retrieved.year == 2024
        assert retrieved.country == "uk"
    
    def test_list_datasets(self, temp_db):
        d1 = SingleYearDataset(year=2024, country="uk")
        d2 = SingleYearDataset(year=2025, country="uk")
        d3 = SingleYearDataset(year=2024, country="us")
        
        temp_db.save_dataset(d1)
        temp_db.save_dataset(d2)
        temp_db.save_dataset(d3)
        
        # List all
        all_datasets = temp_db.list_datasets()
        assert len(all_datasets) == 3
        
        # Filter by country
        uk_datasets = temp_db.list_datasets(country="uk")
        assert len(uk_datasets) == 2
        
        # Filter by year
        datasets_2024 = temp_db.list_datasets(year=2024)
        assert len(datasets_2024) == 2
    
    def test_save_and_get_entity_table(self, temp_db):
        # First create a dataset
        dataset = SingleYearDataset(year=2024, country="uk")
        dataset_id = temp_db.save_dataset(dataset)
        
        # Create and save entity table
        table = EntityTable(entity_type=UKPerson)
        table.add_entity(UKPerson(
            id="p1", age=30, benunit_id="b1", household_id="h1"
        ))
        table.add_entity(UKPerson(
            id="p2", age=25, benunit_id="b1", household_id="h1"
        ))
        
        success = temp_db.save_entity_table(table, "persons", dataset_id)
        assert success is True
        
        # Retrieve
        retrieved = temp_db.get_entity_table(dataset_id, "persons", UKPerson)
        assert retrieved is not None
        assert len(retrieved) == 2
        assert retrieved.entity_type == UKPerson
    
    def test_export_import_parquet(self, temp_db):
        dataset = SingleYearDataset(year=2024, country="uk")
        
        persons = EntityTable(entity_type=UKPerson)
        persons.add_entity(UKPerson(
            id="p1", age=30, benunit_id="b1", household_id="h1"
        ))
        dataset.add_table("persons", persons)
        
        households = EntityTable(entity_type=UKHousehold)
        households.add_entity(UKHousehold(
            id="h1", region="London", tenure_type="rented"
        ))
        dataset.add_table("households", households)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Export
            files = temp_db.export_to_parquet(dataset, tmpdir)
            assert "persons" in files
            assert "households" in files
            assert "metadata" in files
            
            # Import
            entity_types = {
                "persons": UKPerson,
                "households": UKHousehold
            }
            imported = temp_db.import_from_parquet(
                tmpdir, "uk", 2024, entity_types
            )
            
            assert imported.year == 2024
            assert imported.country == "uk"
            assert "persons" in imported.entity_tables
            assert "households" in imported.entity_tables
            assert len(imported.entity_tables["persons"]) == 1
            assert len(imported.entity_tables["households"]) == 1