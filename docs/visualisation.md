# Visualisation utilities

PolicyEngine provides utilities for creating publication-ready charts that follow our visual style guidelines.

## Formatting plotly figures

The `format_fig()` function applies PolicyEngine's visual style to plotly figures, ensuring consistency across all analyses and publications.

```python
from policyengine.utils import format_fig, COLORS
import plotly.graph_objects as go

# Create your figure
fig = go.Figure()
fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Data"))

# Apply PolicyEngine styling
format_fig(
    fig,
    title="Example chart",
    xaxis_title="X axis",
    yaxis_title="Y axis",
    height=600,
    width=800
)

fig.show()
```

## Visual style principles

The formatting applies these principles automatically:

**Colours**: Primary teal (#319795) with semantic colours for different data types (success/green, warning/yellow, error/red, info/blue). Access colours via the `COLORS` dictionary:

```python
from policyengine.utils import COLORS

fig.add_trace(go.Scatter(
    x=x_data,
    y=y_data,
    line=dict(color=COLORS["primary"])
))
```

**Typography**: Inter font family with appropriate sizing (12px for labels, 14px for body text, 16px for titles).

**Layout**: Clean white background with subtle grey gridlines and appropriate margins (48px) for professional presentation.

**Clarity**: Data-driven design that prioritises immediate understanding over decoration.

## Available colours

```python
COLORS = {
    "primary": "#319795",         # Teal (main brand colour)
    "primary_light": "#E6FFFA",
    "primary_dark": "#1D4044",
    "success": "#22C55E",         # Green (positive changes)
    "warning": "#FEC601",         # Yellow (cautions)
    "error": "#EF4444",           # Red (negative changes)
    "info": "#1890FF",            # Blue (neutral information)
    "gray_light": "#F2F4F7",
    "gray": "#667085",
    "gray_dark": "#101828",
    "blue_secondary": "#026AA2",
}
```

## Complete example

See `examples/employment_income_variation.py` for a full demonstration of using `format_fig()` in an analysis workflow.
