import re
from pydantic import RootModel, ValidationError, Field, model_validator
from typing import Dict, TYPE_CHECKING
from annotated_types import Ge, Le
from typing_extensions import Annotated
from typing import Callable
from policyengine_core.simulations import Simulation


class ParametricReform(RootModel):
    """A reform that just changes parameter values."""

    root: Dict[str, Dict | float | bool]
