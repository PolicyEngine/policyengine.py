import importlib.metadata

import pandas as pd

from ..models import Dataset, Dynamic, Model, ModelVersion, Policy


def run_policyengine_us(
    dataset: "Dataset",
    policy: "Policy | None" = None,
    dynamic: "Dynamic | None" = None,
) -> dict[str, "pd.DataFrame"]:
    data: dict[str, pd.DataFrame] = dataset.data

    person_df = pd.DataFrame()

    for table_name, table in data.items():
        if table_name == "person":
            for col in table.columns:
                person_df[f"{col}__{dataset.year}"] = table[col].values
        else:
            foreign_key = data["person"][f"person_{table_name}_id"]
            primary_key = data[table_name][f"{table_name}_id"]

            projected = table.set_index(primary_key).loc[foreign_key]

            for col in projected.columns:
                person_df[f"{col}__{dataset.year}"] = projected[col].values

    from policyengine_us import Microsimulation

    sim = Microsimulation(dataset=person_df)
    sim.default_calculation_period = dataset.year

    def simulation_modifier(sim: Microsimulation):
        if policy is not None and len(policy.parameter_values) > 0:
            for parameter_value in policy.parameter_values:
                sim.tax_benefit_system.parameters.get_child(
                    parameter_value.parameter.id
                ).update(
                    parameter_value.value,
                    start=parameter_value.start_date.strftime("%Y-%m-%d"),
                    stop=parameter_value.end_date.strftime("%Y-%m-%d")
                    if parameter_value.end_date
                    else None,
                )

        if dynamic is not None and len(dynamic.parameter_values) > 0:
            for parameter_value in dynamic.parameter_values:
                sim.tax_benefit_system.parameters.get_child(
                    parameter_value.parameter.id
                ).update(
                    parameter_value.value,
                    start=parameter_value.start_date.strftime("%Y-%m-%d"),
                    stop=parameter_value.end_date.strftime("%Y-%m-%d")
                    if parameter_value.end_date
                    else None,
                )

        if dynamic is not None and dynamic.simulation_modifier is not None:
            dynamic.simulation_modifier(sim)
        if policy is not None and policy.simulation_modifier is not None:
            policy.simulation_modifier(sim)

    simulation_modifier(sim)

    # Skip reforms for now

    output_data = {}

    variable_whitelist = [
        "household_net_income",
    ]

    for variable in variable_whitelist:
        sim.calculate(variable)

    for entity in [
        "person",
        "marital_unit",
        "family",
        "tax_unit",
        "spm_unit",
        "household",
    ]:
        output_data[entity] = pd.DataFrame()
        for variable in sim.tax_benefit_system.variables.values():
            correct_entity = variable.entity.key == entity
            if str(dataset.year) not in list(
                map(str, sim.get_holder(variable.name).get_known_periods())
            ):
                continue
            if variable.definition_period != "year":
                continue
            if not correct_entity:
                continue
            output_data[entity][variable.name] = sim.calculate(variable.name)

    return output_data


policyengine_us_model = Model(
    id="policyengine_us",
    name="PolicyEngine US",
    description="PolicyEngine's open-source tax-benefit microsimulation model.",
    simulation_function=run_policyengine_us,
)

# Get policyengine-uk version


policyengine_us_latest_version = ModelVersion(
    model=policyengine_us_model,
    version=importlib.metadata.distribution("policyengine_us").version,
)
