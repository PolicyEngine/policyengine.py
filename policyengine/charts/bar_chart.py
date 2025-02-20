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
        for attribute in ["x", "y", "color"]:
            column = getattr(self, attribute)
            if column is None:
                continue
            if isinstance(df[column].values[0], Policy):
                df[column] = df[column].apply(lambda x: x.label)
            elif isinstance(df[column].values[0], Dataset):
                df[column] = df[column].apply(lambda x: x.label)
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