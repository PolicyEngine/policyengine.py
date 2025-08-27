from policyengine import Database
from policyengine_uk import Microsimulation, Simulation, Scenario

# Use pe country models as normal

baseline = Microsimulation()
reformed = Microsimulation(scenario=Scenario(parameter_changes={
    "gov.hmrc.income_tax.allowances.personal_allowance.amount": 0,
}))

# Save it into the database

db = Database(connection_string="postgresql://postgres:postgres@127.0.0.1:54322/postgres")
db._auto_initialize()

reform = db.add_scenario(
    name="remove the personal allowance",
    parameter_changes={
        "gov.hmrc.income_tax.allowances.personal_allowance.amount": 0,
    },
    country="uk",
    description="Set the Personal Allowance to zero."
)

current_law = db.get_current_law_scenario(country="uk")
dataset = db.get_dataset(name="enhanced_frs_2023_24", country="uk")

baseline_simulation = db.add_simulation(
    scenario=current_law,
    simulation=baseline,
    dataset=dataset,
    country="uk",
    year=2025,
)

reformed_simulation = db.add_simulation(
    scenario=reform,
    simulation=reformed,
    dataset=dataset,
    country="uk",
    year=2025,
)

report = db.create_report(
    baseline_simulation=baseline_simulation,
    reform_simulation=reformed_simulation,
    year=2025,
    name="remove_personal_allowance_report",
    run_immediately=True
)

baseline_simulation.get_data().person.employment_income