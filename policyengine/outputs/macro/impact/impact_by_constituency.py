from policyengine import Simulation
import plotly.express as px
from policyengine_core.charts import *

def impact_by_constituency(simulation: Simulation):
    """Calculate the revenue impact of the given simulation.

    Args:
        simulation (Simulation): The simulation for which the revenue impact is to be calculated.

    Returns:
        float: The revenue impact of the simulation.
    """
    fig = px.line(x=[1, 2, 3], y=[1, 3, 2])
    return format_fig(fig)