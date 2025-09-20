import pandas as pd

from policyengine.models import Dataset


def create_uk_dataset(
    dataset: str = "enhanced_frs_2023_24.h5",
    year: int = 2029,
):
    from policyengine_uk import Microsimulation

    from policyengine.models.policyengine_uk import policyengine_uk_model

    sim = Microsimulation(
        dataset="hf://policyengine/policyengine-uk-data/" + dataset
    )
    sim.default_calculation_period = year

    tables = {
        "person": pd.DataFrame(sim.dataset[year].person),
        "benunit": pd.DataFrame(sim.dataset[year].benunit),
        "household": pd.DataFrame(sim.dataset[year].household),
    }

    return Dataset(
        id="uk",
        name="UK",
        description="A representative dataset for the UK, based on the Family Resources Survey.",
        year=year,
        model=policyengine_uk_model,
        data=tables,
    )


def create_us_dataset(
    dataset: str = "enhanced_cps_2024.h5",
    year: int = 2024,
):
    from policyengine_us import Microsimulation

    from policyengine.models.policyengine_us import policyengine_us_model

    sim = Microsimulation(
        dataset="hf://policyengine/policyengine-us-data/" + dataset
    )
    sim.default_calculation_period = year

    known_variables = sim.input_variables

    tables = {
        "person": pd.DataFrame(),
        "marital_unit": pd.DataFrame(),
        "tax_unit": pd.DataFrame(),
        "spm_unit": pd.DataFrame(),
        "family": pd.DataFrame(),
        "household": pd.DataFrame(),
    }

    for variable in known_variables:
        entity = sim.tax_benefit_system.variables[variable].entity.key
        if variable in sim.tax_benefit_system.variables:
            tables[entity][variable] = sim.calculate(variable)

    return Dataset(
        id="us",
        name="US",
        description="A representative dataset for the US, based on the Current Population Survey.",
        year=year,
        model=policyengine_us_model,
        data=tables,
    )
