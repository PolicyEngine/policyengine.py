import pandas as pd
from policyengine import Simulation
from policyengine_core.simulations import Microsimulation


def calculate_child_poverty_impacts(simulation: Simulation, count_years: int = 10) -> pd.DataFrame:
    """The change in mean child poverty under baseline vs reform.
    Args:
        simulation: A Simulation object containing baseline and reform scenarios.
        is_child(bool): person level
        in_poverty(bool): spm_unit level
    Returns:
        The change in mean child poverty under baseline vs reform.
    """
    start_year = simulation.options.time_period
    end_year = start_year + count_years

    years = []
    baseline_child_poverty = []
    reform_child_poverty = []
    child_poverty_change = []

    for year in range(start_year, end_year):
        baseline_cp = _get_child_povert_chnage(simulation.baseline_simulation, year).mean()
        reform_cp = _get_child_povert_chnage(simulation.reform_simulation, year).mean()
        years.append(year)
        baseline_child_poverty.append(baseline_cp)
        reform_child_poverty.append(reform_cp)
        child_poverty_change.append(reform_cp - baseline_cp)
    
    return pd.DataFrame({"year": years, "baseline_child_poverty": baseline_child_poverty, "reform_child_poverty": reform_child_poverty, "child_poverty_change": child_poverty_change})


def _get_child_povert_chnage(sim: Microsimulation,
    year: int,):
    is_child = sim.calculate("is_child", period=year)
    in_poverty = sim.calculate("in_poverty", map_to="person", period=year)
    return in_poverty[is_child].mean()
