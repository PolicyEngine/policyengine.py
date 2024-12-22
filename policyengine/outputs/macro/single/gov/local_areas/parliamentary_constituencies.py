from policyengine import Simulation
from policyengine.utils.huggingface import download
import h5py
from microdf import MicroSeries
import pandas as pd
from typing import Callable
from policyengine_core import Microsimulation
from policyengine.utils.maps import plot_hex_map


def parliamentary_constituencies(
    simulation: Simulation,
    metric: Callable[[Microsimulation], MicroSeries] = None,
    chart: bool = False,
    code_index: bool = False,
) -> dict:
    """Calculate the impact of the reform on parliamentary constituencies.

    Args:
        simulation (Simulation): The simulation for which the impact is to be calculated.
        metric (Callable[[Microsimulation], [float]]): A custom function to calculate the impact. This must be called on a Microsimulation and return a float (we will call it for each constituency weight set).
        chart (bool): Whether to return a chart or data.
        code_index (bool): Whether to use the constituency code as the index.

    Returns:
        dict: A dictionary with the impact of the reform on parliamentary constituencies (keys=constituency names, values=metric values).
    """
    if not simulation.options.get("include_constituencies"):
        return {}

    if metric is None:
        metric = lambda sim: sim.calculate("household_net_income").median()
    weights_file_path = download(
        repo="policyengine/policyengine-uk-data",
        repo_filename="parliamentary_constituency_weights.h5",
        local_folder=None,
        version=None,
    )
    constituency_names_file_path = download(
        repo="policyengine/policyengine-uk-data",
        repo_filename="constituencies_2024.csv",
        local_folder=None,
        version=None,
    )
    constituency_names = pd.read_csv(constituency_names_file_path)

    with h5py.File(weights_file_path, "r") as f:
        weights = f[str(simulation.time_period)][...]

    result = {}

    sim = simulation.selected_sim
    original_hh_weight = sim.calculate("household_weight").values

    for constituency_id in range(weights.shape[0]):
        sim.set_input(
            "household_weight",
            sim.default_calculation_period,
            weights[constituency_id],
        )
        sim.get_holder("person_weight").delete_arrays(
            sim.default_calculation_period
        )
        sim.get_holder("benunit_weight").delete_arrays(
            sim.default_calculation_period
        )
        calculation_result = metric(sim)
        code = constituency_names.code.iloc[constituency_id]
        result[constituency_names.set_index("code").loc[code]["name"]] = (
            calculation_result
        )

    sim.get_holder("person_weight").delete_arrays(
        sim.default_calculation_period
    )
    sim.get_holder("benunit_weight").delete_arrays(
        sim.default_calculation_period
    )
    sim.set_input(
        "household_weight", sim.default_calculation_period, original_hh_weight
    )

    if chart:
        return plot_hex_map(result, "parliamentary_constituencies")

    if code_index:
        return {
            constituency_names.set_index("name").loc[name]["code"]: value
            for name, value in result.items()
        }

    return result
