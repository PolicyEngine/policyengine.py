from typing import Dict
from pydantic import BaseModel
import numpy as np

Output = Dict[str, float | None]


def get_change(
    x: Output | Dict[str, Output],
    y: Output | Dict[str, Output],
    relative: bool,
    skip_mismatch: bool = False,
) -> Output | Dict[str, Output]:
    """Take two objects of nested str-float relations and create a similarly-structured object with the differences."""
    if isinstance(x, BaseModel):
        output_class = type(x)
        x = x.model_dump()
    else:
        output_class = dict
    if isinstance(y, BaseModel):
        y = y.model_dump()
    result = {}
    for key in x:
        if isinstance(x[key], dict):
            result[key] = get_change(x[key], y[key], relative=relative)
        elif isinstance(x[key], list):
            try:
                result[key] = list(np.array(y[key]) - np.array(x[key]))
            except:
                result[key] = None
        elif x[key] is None and y[key] is None:
            result[key] = None
        elif x[key] is None:
            if skip_mismatch:
                result[key] = None
            else:
                raise ValueError(f"Key {key} is None in x but not in y")
        elif y[key] is None:
            if skip_mismatch:
                result[key] = None
            else:
                raise ValueError(f"Key {key} is None in y but not in x")
        elif isinstance(x[key], str) or isinstance(y[key], str):
            if x[key] == y[key]:
                result[key] = 0
            else:
                result[key] = f"{x[key]} -> {y[key]}"
        elif not relative:
            result[key] = y[key] - x[key]
        else:
            if x[key] == 0:
                result[key] = 0
            else:
                result[key] = (y[key] - x[key]) / x[key]

    return output_class(**result)
