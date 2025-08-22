"""PolicyEngine - A package to conduct policy analysis using PolicyEngine tax-benefit models."""

__version__ = "0.6.1"

from .database import Database, DatabaseConfig

__all__ = [
    "Database",
    "DatabaseConfig",
]