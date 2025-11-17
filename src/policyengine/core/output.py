from typing import TypeVar

import pandas as pd
from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound="Output")


class Output(BaseModel):
    """Base class for all output templates."""

    def run(self):
        """Calculate and populate the output fields.

        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement run()")


class OutputCollection[T: "Output"](BaseModel):
    """Container for a collection of outputs with their DataFrame representation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    outputs: list[T]
    dataframe: pd.DataFrame
