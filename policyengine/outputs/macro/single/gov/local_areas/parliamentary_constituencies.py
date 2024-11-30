from policyengine import Simulation
from policyengine.utils.huggingface import download
import h5py
from microdf import MicroDataFrame
import pandas as pd

DEFAULT_VARIABLES = [
    "household_net_income",
]


def parliamentary_constituencies(
    simulation: Simulation,
    variables: list = DEFAULT_VARIABLES,
    aggregator: str = "sum",
) -> dict:
    if not simulation.options.get("include_constituencies"):
        return {}
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

    sim_df = simulation.selected.calculate_dataframe(variables)

    result = {}

    for constituency_id in range(weights.shape[0]):
        weighted_df = MicroDataFrame(sim_df, weights=weights[constituency_id])
        code = constituency_names.code.iloc[constituency_id]
        result[constituency_names.set_index("code").loc[code]["name"]] = (
            getattr(weighted_df, aggregator)().to_dict()
        )

    return result
