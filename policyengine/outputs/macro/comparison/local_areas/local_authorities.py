from policyengine import Simulation
import pandas as pd
from policyengine.utils.huggingface import download
import plotly.express as px
from policyengine.utils.charts import *
from policyengine.utils.maps import plot_hex_map
from typing import Callable
from policyengine_core import Microsimulation
from microdf import MicroSeries


def local_authorities(
    simulation: Simulation,
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

    constituency_baseline = simulation.calculate(
        "macro/baseline/gov/local_areas/local_authorities", **kwargs
    )
    constituency_reform = simulation.calculate(
        "macro/reform/gov/local_areas/local_authorities", **kwargs
    )

    result = {}

    for constituency in constituency_baseline:
        result[constituency] = comparator(
            constituency_baseline[constituency],
            constituency_reform[constituency],
        )

    if chart:
        return plot_hex_map(result, "local_authorities")

    return result
