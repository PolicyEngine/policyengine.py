import pandas as pd
from policyengine import Simulation as PolicyEngine # Rename Simulation to PolicyEngine to avoid name conflict
from policyengine_core.simulations import Simulation
from pydantic import BaseModel

class ChildPovertyImpactParameters(BaseModel): # Ask extension developers to validate inputs to their functions
    count_years: int
    start_year: int
    country: str
    reform: dict

def calculate_child_poverty_impacts(
    engine: PolicyEngine, 
    country: str,
    reform: dict,
    count_years: int = 10, 
    start_year: int = 2024,

) -> pd.DataFrame:
    """The change in mean child poverty under baseline vs reform.
    Args:
        engine: A PolicyEngine instance.
        is_child(bool): person level
        in_poverty(bool): spm_unit level
    Returns:
        The change in mean child poverty under baseline vs reform.
    """

    ChildPovertyImpactParameters.model_validate(
        count_years=count_years,
        start_year=start_year,
    )

    baseline_simulation: Simulation = engine.build_simulation(
        name="baseline", # Optionally, we could cache named simulations so we're not rerunning baseline each time. Or not!
        country=country,
        policy={},
        scope="macro",
    )

    reform_simulation: Simulation = engine.build_simulation(
        name="reform",
        country=country,
        policy=reform,
        scope="macro",
    )

    end_year = start_year + count_years

    years = []
    baseline_child_poverty = []
    reform_child_poverty = []
    child_poverty_change = []

    for year in range(start_year, end_year):
        baseline_cp = _get_child_povert_chnage(
            baseline_simulation, year
        ).mean()
        reform_cp = _get_child_povert_chnage(
            reform_simulation, year
        ).mean()
        years.append(year)
        baseline_child_poverty.append(baseline_cp)
        reform_child_poverty.append(reform_cp)
        child_poverty_change.append(reform_cp - baseline_cp)

    return pd.DataFrame(
        {
            "year": years,
            "baseline_child_poverty": baseline_child_poverty,
            "reform_child_poverty": reform_child_poverty,
            "child_poverty_change": child_poverty_change,
        }
    )


def _get_child_povert_chnage(
    sim: Microsimulation,
    year: int,
):
    is_child = sim.calculate("is_child", period=year)
    in_poverty = sim.calculate("in_poverty", map_to="person", period=year)
    return in_poverty[is_child].mean()
