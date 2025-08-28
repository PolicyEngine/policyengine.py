"""US example: Double the federal EITC."""

from policyengine import SimulationOrchestrator
from src.policyengine.sql_storage_adapter import SQLConfig
from policyengine_us import Microsimulation
from policyengine_core.reforms import Reform

# Configure SQL storage
sql_config = SQLConfig(
    connection_string="postgresql://postgres:postgres@127.0.0.1:54322/postgres",
    echo=False,
    storage_mode="local",
    local_storage_path="./simulations",
    default_country="us"
)

# Initialize orchestrator with SQL storage
orchestrator = SimulationOrchestrator(
    storage_method="sql",
    config=sql_config,
    countries=["us"],
    initialize=True
)

# Create scenarios
# First ensure current law exists
orchestrator.create_scenario(
    name="current_law",
    parameter_changes={},
    country="us",
    description="Current US tax and benefit system"
)
current_law = orchestrator.get_current_law_scenario(country="us")
reformed = orchestrator.create_scenario(
    name="double_federal_eitc",
    parameter_changes={
        "gov.irs.credits.eitc.amount.max[0].amount": {"2025-01-01": 1264},  # Double from $632
        "gov.irs.credits.eitc.amount.max[1].amount": {"2025-01-01": 7656},  # Double from $3828
        "gov.irs.credits.eitc.amount.max[2].amount": {"2025-01-01": 8602},  # Double from $4301
        "gov.irs.credits.eitc.amount.max[3].amount": {"2025-01-01": 9680},  # Double from $4840
    },
    country="us",
    description="Double the federal EITC maximum amounts",
)

# Create baseline and reformed simulations
baseline_simulation = orchestrator.create_simulation(
    scenario=current_law,
    simulation=Microsimulation(),
    dataset="enhanced_cps_2024",
    country="us",
    year=2025,
)

# Create reform
def double_eitc(parameters):
    parameters.gov.irs.credits.eitc.amount.max[0].amount.update(start="2025-01-01", value=1264)
    parameters.gov.irs.credits.eitc.amount.max[1].amount.update(start="2025-01-01", value=7656)
    parameters.gov.irs.credits.eitc.amount.max[2].amount.update(start="2025-01-01", value=8602)
    parameters.gov.irs.credits.eitc.amount.max[3].amount.update(start="2025-01-01", value=9680)
    return parameters

reform = Reform.from_dict({
    "gov.irs.credits.eitc.amount.max[0].amount": {"2025-01-01": 1264},
    "gov.irs.credits.eitc.amount.max[1].amount": {"2025-01-01": 7656},
    "gov.irs.credits.eitc.amount.max[2].amount": {"2025-01-01": 8602},
    "gov.irs.credits.eitc.amount.max[3].amount": {"2025-01-01": 9680},
}, country_id="us")

reform_simulation = orchestrator.create_simulation(
    scenario=reformed,
    simulation=Microsimulation(reform=reform),
    dataset="enhanced_cps_2024",
    country="us",
    year=2025,
)

# Create economic impact report
report = orchestrator.create_report(
    baseline_simulation=baseline_simulation,
    reform_simulation=reform_simulation,
    year=2025,
    name="double_eitc_report",
    run_immediately=True
)

print(f"Report '{report.get('name', 'unnamed')}' created successfully!")

# Get report results
results = orchestrator.get_report(report.get('id')) or {}

# Display results
print("\n=== US Economic Impact Report: Double Federal EITC ===")
print(f"\nReport ID: {report.get('id', 'N/A')}")

if "government_budget" in results:
    print("\n1. Government Budget Impact:")
    budget = results["government_budget"]
    if "federal_benefits" in budget:
        print(f"   Federal benefits change: ${budget['federal_benefits']['change']/1e9:.2f}B")
    if "net_impact" in budget:
        print(f"   Net budget impact: ${budget['net_impact']/1e9:.2f}B")

if "household_income" in results:
    print("\n2. Household Income Impact:")
    income = results["household_income"]
    if "household_net_income" in income:
        print(f"   Net income change: ${income['household_net_income']['change']/1e9:.2f}B")

if "poverty_impacts" in results and len(results["poverty_impacts"]) > 0:
    print("\n3. Poverty Impact:")
    for impact in results["poverty_impacts"]:
        if impact["demographic_group"] == "all" and impact["poverty_type"] == "spm":
            print(f"   SPM poverty rate: {impact['rate_baseline']:.1%} → {impact['rate_reform']:.1%} ({impact['rate_change']:.2%} change)")
            break

if "inequality_impacts" in results:
    print("\n4. Inequality Impact:")
    ineq = results["inequality_impacts"]
    if ineq.get("gini_baseline"):
        print(f"   Gini coefficient: {ineq['gini_baseline']:.4f} → {ineq['gini_reform']:.4f} ({ineq['gini_change']:.4f} change)")

if "program_impacts" in results and len(results["program_impacts"]) > 0:
    print("\n5. Program Impacts:")
    for impact in results["program_impacts"]:
        if impact["program_name"] == "EITC":
            print(f"   EITC cost: ${impact['baseline_cost']/1e9:.2f}B → ${impact['reform_cost']/1e9:.2f}B (+${impact['cost_change']/1e9:.2f}B)")
            print(f"   EITC recipients: {impact['baseline_recipients']/1e6:.1f}M → {impact['reform_recipients']/1e6:.1f}M")
            print(f"   Average benefit: ${impact['baseline_average_benefit']:.0f} → ${impact['reform_average_benefit']:.0f}")
            break

print("\n=== End of Report ===")