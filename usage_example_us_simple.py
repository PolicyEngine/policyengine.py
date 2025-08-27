"""Simple US example demonstrating report functionality."""

from policyengine import Database
from policyengine_us import Microsimulation

# Initialize database
db = Database(connection_string="postgresql://postgres:postgres@127.0.0.1:54322/postgres")
db._auto_initialize()

print("Setting up US scenarios...")

# Ensure current law scenario exists
db.add_scenario(
    name="us_current_law",
    parameter_changes={},
    country="us",
    description="Current US tax and benefit system"
)

# Create a test scenario (identical to current law for testing)
db.add_scenario(
    name="us_test_reform",
    parameter_changes={},
    country="us",
    description="Test reform for US report functionality"
)

print("Creating simulations...")

# Create baseline simulation
baseline_sim = db.add_simulation(
    scenario="us_current_law",
    simulation=Microsimulation(),
    dataset="enhanced_cps_2024",
    country="us",
    year=2025,
)

# Create reform simulation (identical for testing)
reform_sim = db.add_simulation(
    scenario="us_test_reform",
    simulation=Microsimulation(),
    dataset="enhanced_cps_2024",
    country="us",
    year=2025,
)

print("Creating economic impact report...")

# Create report
report = db.create_report(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    year=2025,
    name="us_test_report",
    run_immediately=True
)

print(f"\n=== US Economic Impact Report ===")
print(f"Report ID: {report.id}")
print(f"Status: {report.status}")

# Get report results
results = db.get_report_results(report.id)

if "government_budget" in results:
    print("\n1. Government Budget:")
    budget = results["government_budget"]
    print(f"   Federal tax revenue: ${budget['federal_tax']['baseline']/1e9:.1f}B")
    print(f"   Federal benefits: ${budget['federal_benefits']['baseline']/1e9:.1f}B")

if "poverty_impacts" in results and len(results["poverty_impacts"]) > 0:
    print("\n2. Poverty Impact:")
    for impact in results["poverty_impacts"]:
        if impact["demographic_group"] == "all":
            print(f"   Poverty rate: {impact['rate_baseline']:.1%}")
            print(f"   People in poverty: {impact['headcount_baseline']/1e6:.1f}M")
            break

if "program_impacts" in results and len(results["program_impacts"]) > 0:
    print("\n3. Major Program Costs:")
    for impact in sorted(results["program_impacts"], key=lambda x: x["baseline_cost"], reverse=True)[:3]:
        print(f"   {impact['program_name']}: ${impact['baseline_cost']/1e9:.1f}B ({impact['baseline_recipients']/1e6:.1f}M recipients)")

print("\n=== Report Complete ===")