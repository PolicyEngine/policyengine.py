"""Source-line tracking helper for results.json values.

The key traceability guarantee of the blog pipeline is that every
number in a blog post links back to the exact line of code that
produced it.  This module provides a helper that captures the
caller's line number automatically via ``inspect``.
"""

import inspect
from typing import Any


def tracked_value(
    value: Any,
    display: str,
    repo: str,
    filename: str = "analysis.py",
    branch: str = "main",
    *,
    _stack_offset: int = 1,
) -> dict:
    """Build a results.json value entry with automatic source tracking.

    Captures the caller's file and line number so every value in
    results.json points to the code that produced it.

    Args:
        value: The raw numeric value.
        display: Human-readable formatted string (e.g. "$15.2 billion").
        repo: GitHub org/repo (e.g. "PolicyEngine/analyses").
        filename: Script filename within the repo.
        branch: Git branch for the source URL.
        _stack_offset: How many frames to skip (default 1 = caller).

    Returns:
        Dict matching the ValueEntry schema::

            {
                "value": -15200000000,
                "display": "$15.2 billion",
                "source_line": 47,
                "source_url": "https://github.com/.../analysis.py#L47",
            }

    Example::

        from policyengine.results import tracked_value

        budget = reform_revenue - baseline_revenue
        results["values"]["budget_impact"] = tracked_value(
            value=budget,
            display=f"${abs(budget)/1e9:.1f} billion",
            repo="PolicyEngine/analyses",
        )
    """
    frame = inspect.stack()[_stack_offset]
    line = frame.lineno

    source_url = (
        f"https://github.com/{repo}/blob/{branch}/{filename}#L{line}"
    )

    return {
        "value": value,
        "display": display,
        "source_line": line,
        "source_url": source_url,
    }
