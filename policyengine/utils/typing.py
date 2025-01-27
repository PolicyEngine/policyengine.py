from typing import Callable, Type, TypeVar, ParamSpec
from functools import wraps

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")


def add_methods(methods: list[Callable]) -> Callable[[Type[T]], Type[T]]:
    """
    Class decorator that adds methods to a class while preserving their metadata.

    Args:
        methods: List of functions to add as methods
    """

    def decorator(cls: Type[T]) -> Type[T]:
        for method in methods:

            @wraps(method)
            def wrapped(self: T, *args: P.args, **kwargs: P.kwargs) -> R:
                return method(self, *args, **kwargs)

            if getattr(method, "_example_simulation_parameters"):
                setattr(
                    wrapped,
                    "_example_simulation_parameters",
                    method._example_simulation_parameters,
                )

            setattr(cls, method.__name__, wrapped)
        return cls

    return decorator
