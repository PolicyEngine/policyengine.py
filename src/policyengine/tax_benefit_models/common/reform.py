"""Compile a simple reform dict into the format policyengine_core expects.

Accepted shapes for the agent-facing API:

.. code-block:: python

    # Scalar — applied from today onwards.
    reform = {"gov.irs.deductions.salt.cap": 0}

    # With effective date(s).
    reform = {"gov.irs.deductions.salt.cap": {"2026-01-01": 0}}

    # Multiple parameters.
    reform = {
        "gov.irs.deductions.salt.cap": 0,
        "gov.irs.credits.ctc.amount": 2500,
    }

The compiled form is ``{param_path: {period: value}}`` — exactly what
``policyengine_us.Microsimulation(reform=...)`` /
``policyengine_uk.Microsimulation(reform=...)`` accept at construction.
No other input shape is supported.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any, Optional


def compile_reform(
    reform: Optional[Mapping[str, Any]],
) -> Optional[dict[str, dict[str, Any]]]:
    """Compile a simple reform dict to the core reform-dict format."""
    if not reform:
        return None

    today = date.today().isoformat()
    compiled: dict[str, dict[str, Any]] = {}

    for parameter_path, spec in reform.items():
        if isinstance(spec, Mapping):
            compiled[parameter_path] = {str(k): v for k, v in spec.items()}
        else:
            compiled[parameter_path] = {today: spec}

    return compiled
