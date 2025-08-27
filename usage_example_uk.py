from policyengine import SimulationOrchestrator
from policyengine_uk import Microsimulation, Simulation, Scenario

# Use pe country models as normal

baseline = Microsimulation()
reformed = Microsimulation(scenario=Scenario(parameter_changes={
    "gov.hmrc.income_tax.allowances.personal_allowance.amount": 0,
}))

# Save it using the orchestrator

orchestrator = SimulationOrchestrator(connection_string="postgresql://postgres:postgres@127.0.0.1:54322/postgres")
orchestrator._auto_initialize()

reform = orchestrator.add_scenario(
    name="remove the personal allowance",
    parameter_changes={
        "gov.hmrc.income_tax.allowances.personal_allowance.amount": 0,
    },
    country="uk",
    description="Set the Personal Allowance to zero."
)

current_law = orchestrator.get_current_law_scenario(country="uk")
dataset = orchestrator.get_dataset(name="enhanced_frs_2023_24", country="uk")

baseline_simulation = orchestrator.add_simulation(
    scenario=current_law,
    simulation=baseline,
    dataset=dataset,
    country="uk",
    year=2025,
)

reformed_simulation = orchestrator.add_simulation(
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

baseline_simulation.get_data().person.employment_income