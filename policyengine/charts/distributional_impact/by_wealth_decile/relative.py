import plotly.graph_objects as go
from policyengine_core.charts.formatting import *


class ByWealthDecileRelativeChart:
    def __init__(self, country: str, data=None):
        if data is None:
            raise ValueError("Data must be provided")
        
        # Convert the relative values to percentages and store them in attributes for each decile
        for i in range(1, 12):
            setattr(self, f"decile_{i}", data['relative'][i] * 100)

        self.country = country

    def _get_color(self, value):
        if value is None or value == 0 or value < 0:
            return GRAY
        return BLUE

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
        categories = [str(i) for i in range(1, 12)]
        values = [getattr(self, f"decile_{i}") for i in range(1, 12)]
        
        # Filter out categories and values with zero difference
        non_zero_data = [(cat, val) for cat, val in zip(categories, values) if val != 0]
        
        if not non_zero_data:
            fig = go.Figure()
            fig.add_annotation(
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                text="No differences to display",
                showarrow=False,
                font=dict(size=20)
            )
            fig.update_layout(
                title="Relative change in household income",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False)
            )
            return fig

        non_zero_categories, non_zero_values = zip(*non_zero_data)

        # Generate hover texts with formatted impact values and change direction
        hover_texts = [
            f"This reform would {self._get_change_direction(val)} the income of households in the {i}{self.ordinal_suffix(int(i))} decile by {abs(val):,.1f}%"
            for i, val in zip(non_zero_categories, non_zero_values)
        ]

        fig = go.Figure()

        values_in_bn = non_zero_values  # The values are already in percentages
        colors = [self._get_color(value) for value in non_zero_values]

        fig.add_trace(go.Bar(
            x=non_zero_categories,
            y=values_in_bn,
            marker=dict(color=colors, line=dict(width=1)),
            width=0.6,
            text=[f"{value:.1f}%" for value in non_zero_values],  # Display values with one decimal place and percentage symbol
            textposition='outside',
            hovertemplate="<b>Decile %{x}</b><br><br>%{customdata}<extra></extra>",  # Hover shows "Decile {x}"
            customdata=hover_texts
        ))

        # Update layout to show percentage on y-axis and format figure
        fig.update_layout(
            yaxis=dict(
                tickformat=".1f%",  # Format for one decimal place with percentage symbol
                ticksuffix="%",
                title="Relative Impact on Wealth (%)"
            ),
            xaxis=dict(
                title="Wealth Decile"
            ),
            hoverlabel=dict(
                bgcolor="white",
                font=dict(color="black", size=16)
            ),
            title="Relative Change in Household Income by Decile"
        )
        
        format_fig(fig)  # Keep the formatting logic from policyengine_core
        return fig
