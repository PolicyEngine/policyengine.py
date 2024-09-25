import plotly.graph_objects as go
from policyengine_core.charts.formatting import *

class RegularPovertyByAgeChart:
    def __init__(self,country:str, data=None):
        if data is None:
            raise ValueError("Data must be provided")

        self.data = data
    
    def _get_color(self, value):
        # All bars should be gray
        return GRAY

    def _get_change_direction(self, value):
        if value > 0:
            return "increase"
        elif value < 0:
            return "decrease"
        else:
            return "no change"

    def ordinal_suffix(self, n):
        """Return the ordinal suffix for an integer."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return suffix

    def generate_chart_data(self):
        categories = list(self.data.keys())
        values = [self.data[cat]['change'] for cat in categories]
        baselines = [self.data[cat]['baseline'] * 100 for cat in categories]
        reforms = [self.data[cat]['reform'] * 100 for cat in categories]

        # Generate hover texts with baseline, reform, and percentage change
        hover_texts = [
            f"This reform would {self._get_change_direction(val)} the percentage of {category.lower()} in poverty by {abs(val):.1f}% from {baseline:.1f}% to {reform:.1f}%"
            for category, val, baseline, reform in zip(categories, values, baselines, reforms)
        ]

        fig = go.Figure()

        values_in_pct = values  # Use percentage values
        colors = [self._get_color(value) for value in values]

        # Add bar chart with percentage values
        fig.add_trace(go.Bar(
            x=categories,
            y=values_in_pct,
            marker=dict(color=colors, line=dict(width=1)),
            width=0.6,
            text=[f"{abs(value):.1f}%" for value in values],  # Display values as percentages
            textposition='outside',
            hovertemplate="<b>%{x}</b><br><br>%{customdata}<extra></extra>",  # Hover shows category
            customdata=hover_texts
        ))

        # Update layout to reflect percentage values on y-axis
        fig.update_layout(
            yaxis=dict(
                tickformat=",.1f%%",  # Format y-axis as percentages with one decimal place
                title="Percentage Change in Poverty"
            ),
            xaxis=dict(
                title="Category"
            ),
            hoverlabel=dict(
                bgcolor="white",
                font=dict(color="black", size=16)
            ),
            title="Change in Poverty Percentage by Category"
        )
        
        format_fig(fig)  # Keep the formatting logic from policyengine_core
        return fig


# # Example data
# data = {
#     'Child': {
#         'Baseline': 0.32427219591395395,
#         'Reform': 0.33392168532001054,
#         'Change': 3.0
#     },
#     'Adult': {
#         'Baseline': 0.17427822561729264,
#         'Reform': 0.17757158627182623,
#         'Change': 1.9
#     },
#     'Senior': {
#         'Baseline': 0.12817646500651358,
#         'Reform': 0.1370685860340031,
#         'Change': 6.9
#     },
#     'All': {
#         'Baseline': 0.19913534734369268,
#         'Reform': 0.20487670454940832,
#         'Change': 2.9
#     }
# }

# # Generate chart for all categories
# chart = OverallChart(data=data)
# fig = chart.generate_chart_data()
# fig.show()
