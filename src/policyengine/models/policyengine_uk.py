import importlib.metadata

import pandas as pd

from ..models import Dataset, Dynamic, Model, ModelVersion, Policy


def run_policyengine_uk(
    dataset: "Dataset",
    policy: "Policy | None" = None,
    dynamic: "Dynamic | None" = None,
) -> dict[str, "pd.DataFrame"]:
    data: dict[str, pd.DataFrame] = dataset.data

    from policyengine_uk import Microsimulation
    from policyengine_uk.data import UKSingleYearDataset

    pe_input_data = UKSingleYearDataset(
        person=data["person"],
        benunit=data["benunit"],
        household=data["household"],
        fiscal_year=dataset.year,
    )

    sim = Microsimulation(dataset=pe_input_data)
    sim.default_calculation_period = dataset.year

    def simulation_modifier(sim: Microsimulation):
        if policy is not None and len(policy.parameter_values) > 0:
            for parameter_value in policy.parameter_values:
                sim.tax_benefit_system.parameters.get_child(
                    parameter_value.parameter.id
                ).update(
                    value=parameter_value.value,
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
                    value=parameter_value.value,
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

    variable_blacklist = [  # TEMPORARY: we need to fix policyengine-uk to make these only take a long time with non-default parameters set to true.
        "is_uc_entitled_baseline",
        "income_elasticity_lsr",
        "child_benefit_opts_out",
        "housing_benefit_baseline_entitlement",
        "baseline_ctc_entitlement",
        "pre_budget_change_household_tax",
        "pre_budget_change_household_net_income",
        "is_on_cliff",
        "marginal_tax_rate_on_capital_gains",
        "relative_capital_gains_mtr_change",
        "pre_budget_change_ons_equivalised_income_decile",
        "substitution_elasticity",
        "marginal_tax_rate",
        "cliff_evaluated",
        "cliff_gap",
        "substitution_elasticity_lsr",
        "relative_wage_change",
        "relative_income_change",
        "pre_budget_change_household_benefits",
    ]

    for entity in ["person", "benunit", "household"]:
        output_data[entity] = pd.DataFrame()
        for variable in sim.tax_benefit_system.variables.values():
            correct_entity = variable.entity.key == entity
            if variable.name in variable_blacklist:
                continue
            if variable.definition_period != "year":
                continue
            if correct_entity:
                output_data[entity][variable.name] = sim.calculate(
                    variable.name
                )

    return output_data


policyengine_uk_model = Model(
    id="policyengine_uk",
    name="PolicyEngine UK",
    description="PolicyEngine's open-source tax-benefit microsimulation model.",
    simulation_function=run_policyengine_uk,
)

# Get policyengine-uk version

policyengine_uk_latest_version = ModelVersion(
    model=policyengine_uk_model,
    version=importlib.metadata.distribution("policyengine_uk").version,
)
