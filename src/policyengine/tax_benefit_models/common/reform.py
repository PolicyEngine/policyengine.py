"""Compile a simple reform dict into the format policyengine_core expects.

Accepted shapes for the agent-facing API:

.. code-block:: python

    # Scalar — applied from Jan 1 of ``year`` (the simulation year).
    reform = {"gov.irs.deductions.salt.cap": 0}

    # With explicit effective date(s).
    reform = {"gov.irs.deductions.salt.cap": {"2026-01-01": 0}}

    # Multiple parameters.
    reform = {
        "gov.irs.deductions.salt.cap": 0,
        "gov.irs.credits.ctc.amount": 2500,
    }

The compiled form is ``{param_path: {period: value}}`` — exactly what
``policyengine_us.Simulation(reform=...)`` /
``policyengine_uk.Simulation(reform=...)`` accept at construction.

Scalar reforms default to ``{year}-01-01`` so a caller running
mid-year does not accidentally get a blended partial-year result.
Unknown parameter paths raise ``ValueError`` with a close-match
suggestion; pass ``model_version`` to enable the check.
"""

from __future__ import annotations

from collections.abc import Mapping
from difflib import get_close_matches
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion


def compile_reform(
    reform: Optional[Mapping[str, Any]],
    *,
    year: Optional[int] = None,
    model_version: Optional[TaxBenefitModelVersion] = None,
) -> Optional[dict[str, dict[str, Any]]]:
    """Compile a simple reform dict to the core reform-dict format.

    Args:
        reform: Flat mapping from parameter path to either a scalar
            (applied from ``{year}-01-01``) or a ``{effective_date: value}``
            mapping.
        year: Simulation year. Used as the default effective date for
            scalar values so a mid-year call still targets the whole year.
        model_version: If provided, parameter paths are validated
            against ``model_version.parameters_by_name`` and unknown
            paths raise with a close-match suggestion.
    """
    if not reform:
        return None

    default_date = f"{year}-01-01" if year is not None else "1900-01-01"

    if model_version is not None:
        valid = set(model_version.parameters_by_name)
        unknown = [path for path in reform if path not in valid]
        if unknown:
            lines = [
                f"Reform contains parameter paths not defined on "
                f"{model_version.model.id} {model_version.version}:",
            ]
            for path in unknown:
                suggestions = get_close_matches(path, valid, n=1, cutoff=0.7)
                hint = f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
                lines.append(f"  - '{path}'{hint}")
            raise ValueError("\n".join(lines))

    compiled: dict[str, dict[str, Any]] = {}
    for parameter_path, spec in reform.items():
        if isinstance(spec, Mapping):
            compiled[parameter_path] = {str(k): v for k, v in spec.items()}
        else:
            compiled[parameter_path] = {default_date: spec}
    return compiled
