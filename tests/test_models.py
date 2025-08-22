"""Tests for PolicyEngine models."""

import pytest
from datetime import datetime
from policyengine import (
    BaseEntity,
    EntityTable,
    SingleYearDataset,
    Population,
    Scenario,
    UKPerson,
    USPerson,
)


class TestBaseEntity:
    def test_base_entity_creation(self):
        entity = BaseEntity(id="test_1", weight=1.5)
        assert entity.id == "test_1"
        assert entity.weight == 1.5
    
    def test_to_dict(self):
        entity = BaseEntity(id="test_1", weight=2.0)
        data = entity.to_dict()
        assert data["id"] == "test_1"
        assert data["weight"] == 2.0
    
    def test_from_dict(self):
        data = {"id": "test_1", "weight": 1.5}
        entity = BaseEntity.from_dict(data)
        assert entity.id == "test_1"
        assert entity.weight == 1.5


class TestEntityTable:
    def test_entity_table_creation(self):
        table = EntityTable(entity_type=BaseEntity)
        assert len(table) == 0
        assert table.entity_type == BaseEntity
    
    def test_add_entity(self):
        table = EntityTable(entity_type=BaseEntity)
        entity = BaseEntity(id="test_1")
        table.add_entity(entity)
        assert len(table) == 1
    
    def test_add_wrong_entity_type(self):
        table = EntityTable(entity_type=UKPerson)
        entity = BaseEntity(id="test_1")
        with pytest.raises(ValueError):
            table.add_entity(entity)
    
    def test_to_dataframe(self):
        table = EntityTable(entity_type=BaseEntity)
        table.add_entity(BaseEntity(id="test_1", weight=1.0))
        table.add_entity(BaseEntity(id="test_2", weight=2.0))
        
        df = table.to_dataframe()
        assert len(df) == 2
        assert list(df["id"]) == ["test_1", "test_2"]
        assert list(df["weight"]) == [1.0, 2.0]
    
    def test_filter(self):
        table = EntityTable(entity_type=BaseEntity)
        table.add_entity(BaseEntity(id="test_1", weight=1.0))
        table.add_entity(BaseEntity(id="test_2", weight=2.0))
        table.add_entity(BaseEntity(id="test_3", weight=1.0))
        
        filtered = table.filter(weight=1.0)
        assert len(filtered) == 2
        assert all(e.weight == 1.0 for e in filtered)


class TestSingleYearDataset:
    def test_dataset_creation(self):
        dataset = SingleYearDataset(year=2024, country="uk")
        assert dataset.year == 2024
        assert dataset.country == "uk"
        assert len(dataset.entity_tables) == 0
    
    def test_add_table(self):
        dataset = SingleYearDataset(year=2024, country="uk")
        table = EntityTable(entity_type=UKPerson)
        dataset.add_table("persons", table)
        
        assert "persons" in dataset.entity_tables
        assert dataset.get_table("persons") == table
    
    def test_summary(self):
        dataset = SingleYearDataset(year=2024, country="uk")
        
        persons_table = EntityTable(entity_type=UKPerson)
        persons_table.add_entity(UKPerson(
            id="p1", benunit_id="b1", household_id="h1"
        ))
        dataset.add_table("persons", persons_table)
        
        summary = dataset.summary()
        assert summary["year"] == 2024
        assert summary["country"] == "uk"
        assert "persons" in summary["tables"]
        assert summary["tables"]["persons"]["count"] == 1


class TestPopulation:
    def test_population_creation(self):
        pop = Population(name="Test Population", country="uk", year=2024)
        assert pop.name == "Test Population"
        assert pop.country == "uk"
        assert pop.year == 2024
        assert pop.id is not None
    
    def test_add_entity_count(self):
        pop = Population(name="Test", country="uk", year=2024)
        pop.add_entity_count("Person", 1000)
        pop.add_entity_count("Household", 400)
        
        assert pop.entity_counts["Person"] == 1000
        assert pop.entity_counts["Household"] == 400
        assert pop.total_entities() == 1400
    
    def test_summary(self):
        pop = Population(name="Test", country="uk", year=2024)
        pop.add_entity_count("Person", 1000)
        pop.add_entity_count("Household", 400)
        
        summary = pop.summary()
        assert "Test" in summary
        assert "uk" in summary
        assert "2024" in summary
        assert "1,000 Persons" in summary
        assert "400 Households" in summary


class TestScenario:
    def test_scenario_creation(self):
        scenario = Scenario(name="Test Scenario", country="uk")
        assert scenario.name == "Test Scenario"
        assert scenario.country == "uk"
        assert scenario.baseline is False
        assert len(scenario.reforms) == 0
    
    def test_country_validation(self):
        with pytest.raises(ValueError):
            Scenario(name="Test", country="invalid")
    
    def test_add_reform(self):
        scenario = Scenario(name="Test", country="uk")
        scenario.add_reform("tax.income_tax.rate", 0.25, "2024")
        
        assert len(scenario.reforms) == 1
        reform = scenario.reforms[0]
        assert reform.parameter == "tax.income_tax.rate"
        assert reform.value == 0.25
        assert reform.period == "2024"
    
    def test_get_reform_dict(self):
        scenario = Scenario(name="Test", country="uk")
        scenario.add_reform("tax.rate", 0.25, "2024")
        scenario.add_reform("benefit.amount", 1000)
        
        reform_dict = scenario.get_reform_dict()
        assert reform_dict["tax.rate.2024"] == 0.25
        assert reform_dict["benefit.amount"] == 1000
    
    def test_baseline_scenario(self):
        scenario = Scenario(name="Baseline", country="uk", baseline=True)
        assert scenario.baseline is True
        summary = scenario.summary()
        assert "(baseline)" in summary


class TestCountryEntities:
    def test_uk_person(self):
        person = UKPerson(
            id="p1",
            benunit_id="b1",
            household_id="h1"
        )
        assert person.id == "p1"
        assert person.benunit_id == "b1"
        assert person.household_id == "h1"
        # Check that dynamic fields are available
        assert hasattr(person, 'employment_income')
    
    def test_us_person(self):
        person = USPerson(
            id="p1",
            tax_unit_id="t1",
            family_id="f1",
            household_id="h1"
        )
        assert person.id == "p1"
        assert person.tax_unit_id == "t1"
        assert person.family_id == "f1"
        assert person.household_id == "h1"
        # Check that dynamic fields are available
        assert hasattr(person, 'employment_income')