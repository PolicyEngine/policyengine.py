"""Dot-access result containers returned by ``calculate_household``.

A result is intentionally thin: it's a ``dict`` subclass that also
supports attribute access, so callers can write either
``result.tax_unit.income_tax`` or ``result["tax_unit"]["income_tax"]``.
The dict shape keeps JSON serialization trivial.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union


class EntityResult(dict):
    """One entity's computed variables with dict AND attribute access.

    Raises :class:`AttributeError` with the list of available variables
    when a caller accesses an unknown name, so typos surface a
    paste-able fix instead of silently returning ``None``.
    """

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self:
            return self[name]
        available = ", ".join(sorted(self))
        raise AttributeError(
            f"entity has no variable '{name}'. Available: {available}. "
            f"Pass extra_variables=['{name}'] to calculate_household if "
            f"'{name}' is a valid variable on the country model that is "
            f"not in the default output columns."
        )

    def __setattr__(self, name: str, value: Any) -> None:  # pragma: no cover
        self[name] = value


class HouseholdResult(dict):
    """Full household calculation result; one key per entity.

    Singleton entities (``household``, ``tax_unit``, ``benunit``, ...)
    map to a single :class:`EntityResult`; multi-member entities (like
    ``person``) map to a ``list[EntityResult]``.
    """

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self:
            return self[name]
        available = ", ".join(sorted(self))
        raise AttributeError(
            f"no entity '{name}' on this result. Available entities: {available}"
        )

    def __setattr__(self, name: str, value: Any) -> None:  # pragma: no cover
        self[name] = value

    def to_dict(self) -> dict[str, Any]:
        """Return a plain ``dict[str, Any]`` copy suitable for JSON dumps."""

        def _convert(value: Any) -> Any:
            if isinstance(value, EntityResult):
                return dict(value)
            if isinstance(value, list):
                return [_convert(v) for v in value]
            return value

        return {key: _convert(val) for key, val in self.items()}

    def write(self, path: Union[str, Path]) -> Path:
        """Write the result to a JSON file and return the path."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return path
