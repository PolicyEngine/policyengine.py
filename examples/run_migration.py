#!/usr/bin/env python
"""Example script showing how to run migrations to update the database."""

from policyengine.database import Database
from policyengine.migrations import migrate_all, migrate_country


def main():
    # Create an in-memory database (you can use a file path for persistence)
    db = Database("sqlite:///:memory:")
    # Or use a file: db = Database("sqlite:///policyengine.db")
    
    print("Starting database migration...")
    print("-" * 50)
    
    # Option 1: Migrate all countries at once
    print("\nMigrating all countries (UK and US)...")
    migrate_all(db, countries=["uk", "us"], include_datasets=True)
    
    # Option 2: Migrate specific country
    # migrate_country(db, "uk", include_datasets=True)
    # migrate_country(db, "us", include_datasets=True)
    
    print("\n" + "-" * 50)
    print("Migration complete!")
    
    # Show what was migrated
    from policyengine.models import Variable, Parameter, Dataset
    
    variables = db.list(Variable)
    parameters = db.list(Parameter)
    datasets = db.list(Dataset)
    
    print(f"\nDatabase now contains:")
    print(f"  - {len(variables)} variables")
    print(f"  - {len(parameters)} parameters")
    print(f"  - {len(datasets)} datasets")
    
    # Show country breakdown
    uk_vars = [v for v in variables if v.country == "uk"]
    us_vars = [v for v in variables if v.country == "us"]
    
    print(f"\nBy country:")
    print(f"  UK: {len(uk_vars)} variables")
    print(f"  US: {len(us_vars)} variables")
    
    # Show datasets
    print(f"\nDatasets:")
    for ds in datasets:
        print(f"  - {ds.name} ({ds.dataset_type})")


if __name__ == "__main__":
    main()