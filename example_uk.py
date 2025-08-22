#!/usr/bin/env python
"""Example of using PolicyEngine database with UK data."""

from policyengine_uk import Microsimulation
from policyengine import Database

# Create microsimulation
sim = Microsimulation()
sim.calculate("hbai_household_net_income", 2024)
# Create database (PostgreSQL by default)
db = Database(validate_schema=False, countries=["uk"])

# Add simulation with default UK variables
db.add_simulation(
    scenario_name="uk_baseline",
    simulation=sim,
    source_dataset="enhanced_frs_2023_24",
    year=2024,
)