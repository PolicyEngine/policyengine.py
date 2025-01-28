from typing import Dict
from pydantic import BaseModel

Output = Dict[str, float]


def get_change(
    x: Output | Dict[str, Output],
    y: Output | Dict[str, Output],
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
            result[key] = get_change(x[key], y[key])
        else:
            result[key] = y[key] - x[key]

    return output_class(**result)
