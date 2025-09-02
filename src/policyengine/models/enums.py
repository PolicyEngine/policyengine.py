"""Enum types for PolicyEngine models."""

from enum import Enum


class OperationStatus(str, Enum):
    """Status of simulation processing."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DatasetType(str, Enum):
    """Data types for dataset fields."""

    UK = "uk"
    US = "us"
