try:
    from policyengine_uk import Simulation as PolicyEngineUKSimulation
    from policyengine_uk.data.dataset_schema import (
        UKSingleYearDataset as PolicyEngineUKSingleYearDataset,
    )
    from policyengine_uk.model_api import Scenario as PolicyEngineUKScenario

    UK_AVAILABLE = True
except ImportError:
    UK_AVAILABLE = False
    PolicyEngineUKSimulation = None
    PolicyEngineUKSingleYearDataset = None
    PolicyEngineUKScenario = None

from policyengine.models import Dataset, Simulation
from policyengine.models.single_year_dataset import SingleYearDataset

try:
    from microdf import MicroDataFrame

    MICRODF_AVAILABLE = True
except ImportError:
    MICRODF_AVAILABLE = False
    MicroDataFrame = None


def run_uk_simulation(simulation: Simulation) -> Dataset:
    """Run the UK-specific simulation."""
    if not UK_AVAILABLE:
        raise ImportError(
            "policyengine-uk is not installed. "
            "Install it with: pip install 'policyengine[uk]' or pip install policyengine-uk"
        )
    # Implement UK-specific simulation logic here
    sim = _get_simulation(simulation)

    # Hack for now: skip explicit calculation of
    # long-running variables (they're still calculated in lsr sims)

    blacklist = [
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

    output = simulation.dataset.data.copy()

    for variable in sim.tax_benefit_system.variables.values():
        if variable in blacklist:
            continue
        output.tables[variable.entity.key][variable.name] = sim.calculate(
            variable.name
        )

    # Cast to microdf
    output.tables["person"]["weight_value"] = sim.calculate(
        "household_weight", map_to="person"
    )
    output.tables["benunit"]["weight_value"] = sim.calculate(
        "household_weight", map_to="benunit"
    )
    output.tables["household"]["weight_value"] = sim.calculate(
        "household_weight", map_to="household"
    )

    simulation.result = Dataset(
        dataset_type="uk_single_year",
        data=output,
    )


def _apply_uk_parametric_reform(provisions, sim):
    """Apply parametric reforms to UK simulation."""
    try:
        from policyengine_core.periods import instant
    except ImportError:
        raise ImportError(
            "policyengine-core is not installed. "
            "Install it with: pip install 'policyengine[uk]'"
        )

    for provision in provisions:
        parameter_name = provision.parameter.name
        sim.tax_benefit_system.parameters.get_child(parameter_name).update(
            start=instant(provision.start_date.strftime("%Y-%m-%d")),
            stop=(
                instant(provision.end_date.strftime("%Y-%m-%d"))
                if provision.end_date
                else None
            ),
            value=provision.value,
        )


def _get_simulation(simulation: Simulation):
    def modifier(sim):
        # Apply parametric reforms
        if simulation.policy.parameter_values:
            _apply_uk_parametric_reform(
                simulation.policy.parameter_values, sim
            )
        if simulation.policy.simulation_modifier:
            simulation.policy.simulation_modifier(sim)

        if simulation.dynamic.parameter_values:
            _apply_uk_parametric_reform(
                simulation.dynamic.parameter_values, sim
            )
        if simulation.dynamic.simulation_modifier:
            simulation.dynamic.simulation_modifier(sim)

    scenario = PolicyEngineUKScenario(simulation_modifier=modifier)
    sim = PolicyEngineUKSimulation(
        dataset=PolicyEngineUKSingleYearDataset(
            person=simulation.dataset.data.tables["person"],
            benunit=simulation.dataset.data.tables["benunit"],
            household=simulation.dataset.data.tables["household"],
            fiscal_year=simulation.dataset.data.year,
        ),
        scenario=scenario,
    )
    sim.default_calculation_period = simulation.dataset.data.year
    return sim
