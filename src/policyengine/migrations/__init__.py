"""Simple migrations API.

Import the functions below for programmatic use:

    from policyengine.migrations import seed_model, seed_datasets

Or run the CLI:

    pe-migrate seed-model uk
    pe-migrate seed-datasets uk efrs --version 2024.1
"""

from .runner import seed_model, seed_datasets, main as cli_main


def seed_us_model(db):
    return seed_model(db, "us")


def seed_uk_model(db):
    return seed_model(db, "uk")


def seed_uk_efrs_datasets(
    db,
    version: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
):
    return seed_datasets(
        db,
        "uk",
        family="efrs",
        version=version,
        start_year=start_year,
        end_year=end_year,
    )


def seed_us_ecps_datasets(
    db,
    version: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
):
    return seed_datasets(
        db,
        "us",
        family="ecps",
        version=version,
        start_year=start_year,
        end_year=end_year,
    )


__all__ = [
    "seed_model",
    "seed_datasets",
    "seed_us_model",
    "seed_uk_model",
    "seed_uk_efrs_datasets",
    "seed_us_ecps_datasets",
    "cli_main",
]
