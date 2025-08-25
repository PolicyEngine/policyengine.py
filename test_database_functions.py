"""Test the new database functions."""

from src.policyengine.database import Database, DatabaseConfig
import pandas as pd
import numpy as np
from datetime import datetime
import traceback

def test_database_functions():
    """Test all the new database functions."""
    
    # Create database with UK as default country
    config = DatabaseConfig(
        connection_string="sqlite:///test_full_db.db",
        echo=False,
        local_storage_path="./test_simulations"
    )
    
    # Test with single country (becomes default) - auto-initializes
    db = Database(config, countries=["uk"], initialize=False)  # Disable auto-init for testing
    
    # Clear database
    db.drop_all()
    db.init_db()
    
    print("=== Testing Database Functions ===\n")
    
    # 1. Initialize with current law
    print("1. Initializing current law parameters...")
    try:
        db.initialize_with_current_law(max_parameters=50)
        print("   ✓ Current law initialized (country defaults to UK)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 2. Add a parametric scenario
    print("\n2. Adding parametric scenario...")
    try:
        param_changes = {
            "gov.hmrc.income_tax.rates.uk.basic": 0.25,  # Simple value
            "gov.hmrc.income_tax.rates.uk.higher": {
                "2024-01-01.2025-12-31": 0.45,  # Date range
                "2026-01-01.2027-12-31": 0.42
            }
        }
        scenario = db.add_parametric_scenario(
            name="basic_rate_reform",
            parameter_changes=param_changes,
            description="Reform to change basic and higher tax rates"
        )
        print(f"   ✓ Created scenario: {scenario.name} with {len(param_changes)} parameter changes")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 3. Get scenario
    print("\n3. Retrieving scenario...")
    try:
        retrieved = db.get_scenario("basic_rate_reform")
        if retrieved:
            print(f"   ✓ Retrieved scenario: {retrieved.name}")
            print(f"     ID: {retrieved.id[:8]}...")
            print(f"     Country: {retrieved.country}")
        else:
            print("   ✗ Scenario not found")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 4. Add dataset
    print("\n4. Adding dataset...")
    try:
        dataset = db.add_dataset(
            name="frs_2023_24",
            year=2023,
            source="FRS",
            version="2023.24",
            description="Family Resources Survey 2023-24"
        )
        print(f"   ✓ Added dataset: {dataset.name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 5. Create and store simulation
    print("\n5. Storing simulation results...")
    try:
        # Create a mock simulation object for testing
        from policyengine_uk import Simulation
        
        test_simulation = Simulation(
            situation={
                "people": {
                    "person1": {
                        "age": {"2024": 30},
                        "employment_income": {"2024": 30000}
                    }
                },
                "benunit": {
                    "members": ["person1"],
                },
                "household": {
                    "members": ["person1"]
                }
            }
        )
        
        sim_result = db.add_simulation(
            scenario="basic_rate_reform",
            simulation=test_simulation,
            dataset="frs_2023_24",
            year=2024,
            tags=["tax_reform", "basic_rate"]
        )
        print(f"   ✓ Stored simulation: {sim_result.id[:8]}...")
        print(f"     File size: {sim_result.file_size_mb:.2f} MB")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        raise e
    
    # 6. Retrieve simulation
    print("\n6. Retrieving simulation...")
    try:
        retrieved_sim = db.get_simulation(
            scenario="basic_rate_reform",
            dataset="frs_2023_24",
            year=2024
        )
        if retrieved_sim:
            print(f"   ✓ Retrieved simulation: {retrieved_sim['id'][:8]}...")
            print(f"     Contains data keys: {list(retrieved_sim['data'].keys())}")
            
            # Verify data integrity
            household_df = retrieved_sim['data']['household']
            if isinstance(household_df, pd.DataFrame):
                print(f"     Household data shape: {household_df.shape}")
        else:
            print("   ✗ Simulation not found")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 7. Test with multiple countries
    print("\n7. Testing multiple country support and auto-initialization...")
    db_multi = Database(config, countries=["uk", "us"], initialize=True, max_init_parameters=10)
    
    try:
        # Check if auto-initialization worked
        uk_current = db_multi.get_current_law_scenario("uk")
        us_current = db_multi.get_current_law_scenario("us")
        
        if uk_current:
            print(f"   ✓ Auto-initialized UK current law: {uk_current.name}")
        if us_current:
            print(f"   ✓ Auto-initialized US current law: {us_current.name}")
        
        # Add US dataset (country must be specified when multiple countries)
        us_dataset = db_multi.add_dataset(
            name="cps_2023",
            country="us",
            year=2023,
            source="CPS",
            description="Current Population Survey 2023"
        )
        print(f"   ✓ Added US dataset: {us_dataset.name}")
        
        # Test default country (should be UK when both are present)
        print(f"   ✓ Default country is: {db_multi.default_country}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n=== All tests completed ===")
    
    # Clean up
    import os
    import shutil
    if os.path.exists("test_full_db.db"):
        os.remove("test_full_db.db")
    if os.path.exists("./test_simulations"):
        shutil.rmtree("./test_simulations")

if __name__ == "__main__":
    test_database_functions()