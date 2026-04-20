"""PolicyEngine brand colours and typography tokens.

Lives outside ``plotting`` so consumers can import ``COLORS`` without
pulling plotly in.
"""

COLORS = {
    "primary": "#319795",  # Teal
    "primary_light": "#E6FFFA",
    "primary_dark": "#1D4044",
    "success": "#22C55E",  # Green (positive changes)
    "warning": "#FEC601",  # Yellow (cautions)
    "error": "#EF4444",  # Red (negative changes)
    "info": "#1890FF",  # Blue (neutral info)
    "gray_light": "#F2F4F7",
    "gray": "#667085",
    "gray_dark": "#101828",
    "blue_secondary": "#026AA2",
}

FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
FONT_SIZE_LABEL = 12
FONT_SIZE_DEFAULT = 14
FONT_SIZE_TITLE = 16
