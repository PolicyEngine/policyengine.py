import typing
if typing.TYPE_CHECKING:
    from policyengine import Simulation
import pandas as pd
from policyengine.utils.huggingface import download
import plotly.express as px
from policyengine.utils.charts import *
from policyengine.utils.maps import plot_hex_map
from typing import Callable
from policyengine_core import Microsimulation
from microdf import MicroSeries
from ...single.gov.local_areas.parliamentary_constituencies import calculate_parliamentary_constituencies


def parliamentary_constituencies(
    simulation: "Simulation",
    chart: bool = False,
    metric: Callable[[Microsimulation], MicroSeries] = None,
    comparator: bool = None,
) -> dict:
    if not simulation.options.get("include_constituencies"):
        return {}

    kwargs = {}
    if metric is not None:
        kwargs["metric"] = metric

    if comparator is None:
        comparator = lambda x, y: (y / x) - 1
    simulation.selected_sim = simulation.baseline_sim
    constituency_baseline = calculate_parliamentary_constituencies(simulation, **kwargs)
    simulation.selected_sim = simulation.reformed_sim
    constituency_reform = calculate_parliamentary_constituencies(simulation, **kwargs)

    result = {}

    for constituency in constituency_baseline:
        result[constituency] = comparator(
            constituency_baseline[constituency],
            constituency_reform[constituency],
        )

    if chart:
        return plot_hex_map(result, "parliamentary_constituencies")

    return result
