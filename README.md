# PolicyEngine

A Python package for conducting policy analysis using PolicyEngine tax-benefit models. This package provides standardised tools for creating and managing single-year datasets from country-specific tax-benefit models.

## Features

- **Standardised entity models** for persons, households, and country-specific units
- **SQLAlchemy-based database** supporting both local (SQLite) and cloud (PostgreSQL/MySQL) storage
- **Country-specific schemas** for UK and US tax-benefit systems
- **Population and scenario management** for simulation runs
- **Export/import functionality** for Parquet files

## Installation

```bash
pip install policyengine
```

## Quick start

```python
from policyengine import Database, Population, Scenario, SingleYearDataset
from policyengine import UKPerson, UKHousehold, EntityTable

# Create database (defaults to SQLite)
db = Database()

# Create a population
population = Population(name="UK 2024", country="uk", year=2024)
population.add_entity_count("Person", 66_000_000)
population.add_entity_count("Household", 28_000_000)
db.save_population(population)

# Create a scenario with reforms
scenario = Scenario(name="Income tax reform", country="uk")
scenario.add_reform("tax.income_tax.rate", 0.25, "2024")
db.save_scenario(scenario)

# Create a dataset with entities
dataset = SingleYearDataset(year=2024, country="uk")

persons = EntityTable(entity_type=UKPerson)
persons.add_entity(UKPerson(
    id="person_1",
    age=35,
    employment_income=30000,
    benunit_id="benunit_1",
    household_id="household_1"
))

households = EntityTable(entity_type=UKHousehold)
households.add_entity(UKHousehold(
    id="household_1",
    region="London",
    tenure_type="rented",
    rent=1500
))

dataset.add_table("persons", persons)
dataset.add_table("households", households)

# Save to database
db.save_dataset(dataset, population_id=population.id)
```

## Database configuration

### Local SQLite (default)
```python
from policyengine import Database
db = Database()  # Creates policyengine.db in current directory
```

### PostgreSQL
```python
from policyengine import Database, DatabaseConfig

config = DatabaseConfig(
    connection_string="postgresql://user:password@localhost/policyengine"
)
db = Database(config)
```

### MySQL
```python
config = DatabaseConfig(
    connection_string="mysql+pymysql://user:password@localhost/policyengine"
)
db = Database(config)
```

## Entity schemas

### UK entities
- `UKPerson`: Individual person with income, benefits, and tax attributes
- `UKBenUnit`: Benefit unit for welfare calculations
- `UKHousehold`: Household with housing costs and regional information

### US entities
- `USPerson`: Individual person with federal and state tax attributes
- `USTaxUnit`: Tax filing unit
- `USFamily`: Family unit for benefit determination
- `USHousehold`: Household with state and local attributes

## Working with datasets

### Export to Parquet
```python
dataset = db.get_dataset(dataset_id="...")
files = db.export_to_parquet(dataset, "/path/to/output")
```

### Import from Parquet
```python
entity_types = {
    "persons": UKPerson,
    "households": UKHousehold
}
dataset = db.import_from_parquet("/path/to/input", "uk", 2024, entity_types)
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
```

## License

GNU Affero General Public License v3.0

## Documentation

Read the full documentation [here](https://policyengine.github.io/policyengine.py).
