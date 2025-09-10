# Creating custom output tables and models

PolicyEngine now supports adding custom output tables and models without modifying core code. This allows you to extend the system with domain-specific metrics and analyses.

## Overview

The custom output system consists of:
- **Models**: Pydantic classes that define the data structure and computation logic
- **Tables**: SQLModel classes that define database storage
- **Registry**: A central system that manages model/table mappings
- **Mappers**: Optional functions to convert between models and tables

## Basic example

Here's how to create a custom poverty gap metric:

```python
from policyengine.models.report_items import ReportElementDataItem
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

# 1. Define your database table
class PovertyGapTable(SQLModel, table=True):
    __tablename__ = "reportitem_poverty_gap"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    simulation_id: UUID = Field(foreign_key="simulations.id")
    country: str
    poverty_line: float
    poverty_gap_index: float

# 2. Define your model
class PovertyGap(ReportElementDataItem):
    simulation: Simulation
    country: str
    poverty_line: float
    poverty_gap_index: float | None = None
    
    @staticmethod
    def run(items: list["PovertyGap"]) -> list["PovertyGap"]:
        # Implement computation logic
        results = []
        for item in items:
            # Calculate poverty gap from simulation data
            # ...
            results.append(item)
        return results
```

## Step-by-step guide

### 1. Create your table class

Your table must inherit from `SQLModel` with `table=True`:

```python
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

class MyCustomTable(SQLModel, table=True):
    __tablename__ = "reportitem_my_custom"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    simulation_id: UUID = Field(foreign_key="simulations.id")
    # Add your fields here
    value: float
    metadata: dict = Field(default={}, sa_type=JSON)
```

### 2. Create your model class

Your model must inherit from `ReportElementDataItem`:

```python
from policyengine.models.report_items import ReportElementDataItem
from policyengine.models.simulation import Simulation

class MyCustomMetric(ReportElementDataItem):
    simulation: Simulation
    value: float | None = None
    
    @staticmethod
    def run(items: list["MyCustomMetric"]) -> list["MyCustomMetric"]:
        """Compute values for provided items."""
        results = []
        for item in items:
            # Access simulation data
            data = item.simulation.result.data
            
            # Perform calculations
            computed_value = calculate_something(data)
            
            # Return new instance with computed value
            results.append(MyCustomMetric(
                simulation=item.simulation,
                value=computed_value,
            ))
        return results
```

### 3. Register your custom type

Register with the database:

```python
from policyengine.database import Database

db = Database("sqlite:///my_database.db")
db.register_custom_mapping(
    model_class=MyCustomMetric,
    table_class=MyCustomTable,
)
```

### 4. Use your custom type

Once registered, use it like any built-in type:

```python
# Create instances
metric = MyCustomMetric(
    simulation=my_simulation,
    # ... other fields
)

# Compute values
results = MyCustomMetric.run([metric])

# Store in database
db.add(results[0])

# Query from database
stored = db.get(MyCustomMetric, id=some_id)
```

## Advanced features

### Custom mappers

For complex conversions between models and tables, provide custom mapper functions:

```python
def my_metric_to_table(item: MyCustomMetric, session, cascade: bool) -> MyCustomTable:
    """Convert model to table with custom logic."""
    # Custom conversion logic
    return MyCustomTable(
        simulation_id=item.simulation.id,
        value=item.value,
        # Transform data as needed
    )

def my_metric_from_table(row: MyCustomTable, session, cascade: bool) -> MyCustomMetric:
    """Convert table to model with custom logic."""
    # Custom reconstruction logic
    return MyCustomMetric(
        simulation=get_simulation(row.simulation_id),
        value=row.value,
    )

# Register with the database including mappers
db.register_custom_mapping(
    model_class=MyCustomMetric,
    table_class=MyCustomTable,
    to_table_mapper=my_metric_to_table,
    from_table_mapper=my_metric_from_table,
)
```

### Accessing simulation data

Within your `run` method, access simulation result data:

```python
@staticmethod
def run(items: list["MyMetric"]) -> list["MyMetric"]:
    for item in items:
        # Get SingleYearDataset from simulation
        data = item.simulation.result.data
        
        # Access entity tables
        person_table = data.tables["person"]
        household_table = data.tables["household"]
        
        # Use weights if available
        if "weight_value" in person_table.columns:
            weights = person_table["weight_value"]
        
        # Access variables
        income = person_table["employment_income"]
        
        # Perform calculations...
```

### Working with filters and aggregations

Follow the pattern of built-in types like `Aggregate`:

```python
class FilteredMetric(ReportElementDataItem):
    simulation: Simulation
    variable: str
    filter_variable: str | None = None
    filter_value: Any | None = None
    
    @staticmethod
    def run(items: list["FilteredMetric"]) -> list["FilteredMetric"]:
        for item in items:
            data = item.simulation.result.data
            df = data.tables["person"]
            
            # Apply filters
            if item.filter_variable and item.filter_value is not None:
                mask = df[item.filter_variable] == item.filter_value
                df = df[mask]
            
            # Compute metric on filtered data
            result_value = df[item.variable].mean()
            # ...
```

## Best practices

1. **Inherit from ReportElementDataItem**: This provides standard DataFrame conversion methods
2. **Implement the run method**: Batch computation for efficiency
3. **Use UUID primary keys**: Consistent with PolicyEngine's schema
4. **Include simulation_id foreign key**: Links your data to simulations
5. **Handle missing data gracefully**: Check for None values and missing columns
6. **Document your metrics**: Include docstrings explaining what your metric measures
7. **Test thoroughly**: Ensure your custom types work with different data scenarios

## Complete example

See `examples/custom_report_item.py` for a complete working example of a poverty gap metric that:
- Defines table and model classes
- Implements computation logic
- Provides custom mappers
- Demonstrates usage patterns

## Troubleshooting

**Table not created**: Ensure you've called `db.register_custom_mapping()` before trying to store data.

**Import errors**: Make sure your custom classes are imported before using them with the database.

**Computation errors**: Check that simulation result data is available and has expected structure.

**Foreign key errors**: Ensure the simulation is saved to the database before saving custom metrics that reference it.