from policyengine import Simulation
import pandas as pd
from policyengine.utils.huggingface import download
import plotly.express as px
from policyengine.utils.charts import *
from policyengine.utils.maps import plot_hex_map
from typing import Callable
from policyengine_core import Microsimulation
from microdf import MicroSeries
from ...single.gov.local_areas.local_authorities import (
    calculate_local_authorities,
)


def local_authorities(
    simulation: "Simulation",
    chart: bool = False,
    metric: Callable[[Microsimulation], MicroSeries] = None,
    comparator: bool = None,
) -> dict:
    if not simulation.options.get("include_local_authorities"):
        return {}

    kwargs = {}
    if metric is not None:
        kwargs["metric"] = metric

    if comparator is None:
        comparator = lambda x, y: (y / x) - 1

    simulation.selected_sim = simulation.baseline_sim
    constituency_baseline = calculate_local_authorities(simulation, **kwargs)
    simulation.selected_sim = simulation.reformed_sim
    constituency_reform = calculate_local_authorities(simulation, **kwargs)

    result = {}

    for constituency in constituency_baseline:
        result[constituency] = comparator(
            constituency_baseline[constituency],
            constituency_reform[constituency],
        )

    if chart:
        return plot_hex_map(result, "local_authorities")

    return result
