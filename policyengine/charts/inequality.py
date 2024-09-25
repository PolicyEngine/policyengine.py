import plotly.graph_objects as go
from policyengine_core.charts.formatting import *

class InequalityImpactChart:
    def __init__(self, data=None) -> None:
        if data is None:
            raise ValueError("Data must be provided")
        
        # Expecting data to contain baseline, reform, change, and change_percentage for each metric
        self.data = data
    
    def generate_chart_data(self):
        # Data for the x-axis labels
        metrics = ["Gini index", "Top 1% share", "Top 10% share"]
        
        # Extract the change percentages, baseline, and reform values for hover text
        change_percentages = [self.data[metric]['change_percentage'] for metric in metrics]
        baseline_values = [self.data[metric]['baseline'] for metric in metrics]
        reform_values = [self.data[metric]['reform'] for metric in metrics]
        
        # Generate hover text for each metric
        hover_texts = [
            f"The reform would increase the {metric} by {change_percentages[i]}% from {baseline_values[i]} to {reform_values[i]}%"
            if change_percentages[i] > 0
            else f"The reform would decrease the {metric} by {change_percentages[i]}% from {baseline_values[i]} to {reform_values[i]}%"
            for i, metric in enumerate(metrics)
        ]
        
        # Create the bar chart figure
        fig = go.Figure()
        
        # Add a bar trace for the change percentages of each metric
        fig.add_trace(go.Bar(
            x=metrics,  # Labels for each metric
            y=change_percentages,  # Change percentages for each metric
            marker=dict(
                color=[BLUE if change_percentages[i] > 0 else GRAY for i in range(len(change_percentages))],  # Conditional color for each bar
                line=dict(width=1),
            ),
            text=[f"{percent}%" for percent in change_percentages],  # Display percentage as text
            textposition='outside',  # Position text outside the bars
            hovertemplate=f"<b>%{{x}}</b><br><br>%{{customdata}}<extra></extra>",  
            customdata=hover_texts  # Hover text for each bar
        ))
        
        # Update layout for the chart
        fig.update_layout(
            yaxis=dict(
                tickformat=".1f",  # Show y-values with one decimal place
                ticksuffix="%",
                title="Relative change"  # Add percentage symbol
            ),
            hoverlabel=dict(
                bgcolor="white",      # Background color of the hover label
                font=dict(
                    color="black",  # Text color of the hover label
                    size=16,        # Font size
                ),
            ),
            title="Impact of Reform on Inequality Metrics"  # Add a title to the chart
        )

        format_fig(fig)
        
        return fig