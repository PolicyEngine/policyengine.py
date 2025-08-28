from policyengine import SimulationOrchestrator
from src.policyengine.sql_storage_adapter import SQLConfig
from policyengine_uk import Microsimulation, Simulation, Scenario

# Use pe country models as normal

baseline = Microsimulation()
reformed = Microsimulation(scenario=Scenario(parameter_changes={
    "gov.hmrc.income_tax.allowances.personal_allowance.amount": 0,
}))

# Save it using the orchestrator

# Configure SQL storage
sql_config = SQLConfig(
    connection_string="postgresql://postgres:postgres@127.0.0.1:54322/postgres",
    echo=False,
    storage_mode="local",
    local_storage_path="./simulations",
    default_country="uk"
)

# Initialize orchestrator with SQL storage
orchestrator = SimulationOrchestrator(
    storage_method="sql",
    config=sql_config,
    countries=["uk"],
    initialize=True
)

reform = orchestrator.create_scenario(
    name="remove the personal allowance",
    parameter_changes={
        "gov.hmrc.income_tax.allowances.personal_allowance.amount": 0,
    },
    country="uk",
    description="Set the Personal Allowance to zero."
)

current_law = orchestrator.get_current_law_scenario(country="uk")
dataset = orchestrator.get_dataset(name="enhanced_frs_2023_24", country="uk")

baseline_simulation = orchestrator.create_simulation(
    scenario=current_law,
    simulation=baseline,
    dataset=dataset,
    country="uk",
    year=2025,
)

reformed_simulation = orchestrator.create_simulation(
    scenario=reform,
    simulation=reformed,
    dataset=dataset,
    country="uk",
    year=2025,
)

report = orchestrator.create_report(
    baseline_simulation=baseline_simulation,
    reform_simulation=reformed_simulation,
    year=2025,
    name="remove_personal_allowance_report",
    run_immediately=True
)

# Access the actual simulation object if needed
# baseline_simulation_data = baseline.calculate("employment_income")