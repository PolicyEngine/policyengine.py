from policyengine.model_api import Chart, Policy, Dataset
from policyengine.model_api.chart import *
import plotly.express as px

class BarChart(Chart):
    x: str
    y: str
    color: str = None
    barmode: str = "group"
    positive_color: str = BLUE
    negative_color: str = DARK_GRAY

    def create(self):
        df = self.df
        fig = px.bar(
            df,
            x=self.x,
            y=self.y,
            color=self.color,
        ).update_layout(
            title=self.title,
        ).update_traces(
            marker_color=[self.positive_color if y > 0 else self.negative_color for y in df[self.y]],
        )

        self.format(fig)

        return fig