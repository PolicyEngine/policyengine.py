"""Parametric reform utilities.

Note: This module is deprecated. Use the country-specific implementations
in the simulation modules instead.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policyengine.models import ParameterValue


def apply_parametric_reform(provisions: list["ParameterValue"]) -> None:
    """Deprecated. Use country-specific implementations instead."""
    raise NotImplementedError(
        "apply_parametric_reform has been moved to country-specific modules. "
        "This function should not be called directly."
    )
