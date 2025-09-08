"""Migration runner for updating database with latest tax-benefit model metadata and datasets."""

from typing import Iterable
from policyengine.database import Database
from policyengine.utils.metadata import get_metadata
from policyengine.utils.version import get_model_version
from policyengine.utils.hugging_face import hf_list_tags
from tqdm import trange


def migrate_country(
    db: Database, country: str, include_datasets: bool = True
) -> None:
    """Migrate a specific country's metadata and datasets to the database.

    This function updates the database with the latest metadata from the installed
    country package, including parameters, variables, and optionally datasets.

    Args:
        db: Database instance to migrate
        country: Country code ("uk" or "us")
        include_datasets: Whether to also migrate datasets (default True)
    """
    country = country.lower()

    # Get the country-specific tax-benefit system
    if country == "uk":
        try:
            from policyengine_uk import CountryTaxBenefitSystem

            system = CountryTaxBenefitSystem()
        except ImportError:
            raise ImportError(
                "policyengine-uk is not installed. "
                "Install it with: pip install 'policyengine[uk]' or pip install policyengine-uk"
            )
    elif country == "us":
        try:
            from policyengine_us import CountryTaxBenefitSystem

            system = CountryTaxBenefitSystem()
        except ImportError:
            raise ImportError(
                "policyengine-us is not installed. "
                "Install it with: pip install 'policyengine[us]' or pip install policyengine-us"
            )
    else:
        raise ValueError(f"Unknown country: {country}")

    # Get metadata using the helper function
    metadata = get_metadata(system, country)
    version = get_model_version(country)

    print(f"Migrating {country.upper()} metadata (version {version})...")

    # Migrate policy and dynamic anchors
    anchor_objs = []
    if metadata.get("current_law") is not None:
        metadata["current_law"].country = country
        anchor_objs.append(metadata["current_law"])
    if metadata.get("static") is not None:
        metadata["static"].country = country
        anchor_objs.append(metadata["static"])
    if anchor_objs:
        print(f"  Migrating {len(anchor_objs)} policy/dynamic anchors...")
        db.add_all(anchor_objs, refresh=False)

    # Migrate variables (upsert on name, country)
    variables = []
    for v in metadata.get("variables", []) or []:
        v.country = country
        variables.append(v)
    if variables:
        print(f"  Migrating {len(variables)} variables...")
        db.add_all(variables, refresh=False, chunk_size=1000, progress=True)

    # Extract unique parameters from parameter values and migrate them
    unique_params = {}
    for pv in metadata.get("parameter_values", []) or []:
        if pv.parameter is not None:
            key = (pv.parameter.name, country)
            if key not in unique_params:
                pv.parameter.country = country
                unique_params[key] = pv.parameter

    if unique_params:
        print(f"  Migrating {len(unique_params)} parameters...")
        db.add_all(
            unique_params.values(),
            refresh=False,
            chunk_size=1000,
            progress=True,
        )

    # Delete existing parameter values for this model version
    print(
        f"  Deleting existing parameter values for model version {version}..."
    )
    deleted_count = db.delete_baseline_parameter_values_by_model_version(
        version, country
    )
    if deleted_count > 0:
        print(f"    Deleted {deleted_count} existing parameter values")

    # Build parameter lookup map
    print(f"  Building parameter lookup map...")
    param_lookup = {}
    from policyengine.tables import ParameterTable
    from sqlmodel import select

    with db.session() as s:
        # Get all parameters for this country in a single query
        param_names = [name[0] for name in unique_params.keys()]
        all_params = s.exec(
            select(ParameterTable).where(
                ParameterTable.name.in_(param_names),
                ParameterTable.country == country,
            )
        ).all()
        
        # Build lookup map from query results
        for param in all_params:
            param_lookup[param.name] = param.id
        
        print(f"    Found {len(param_lookup)} parameters in database")

    # Now add new parameter values directly using bulk insert
    from policyengine.tables import BaselineParameterValueTable
    from sqlalchemy import insert as sa_insert
    import uuid

    pv_rows = []
    for pv in metadata.get("parameter_values", []) or []:
        if pv.parameter is not None and pv.parameter.name in param_lookup:
            pv_rows.append(
                {
                    "id": uuid.uuid4(),
                    "parameter_id": param_lookup[pv.parameter.name],
                    "model_version": version,
                    "start_date": pv.start_date,
                    "end_date": pv.end_date,
                    "value": db._json_safe_value(pv.value),
                    "country": country,
                }
            )

    if pv_rows:
        print(f"  Adding {len(pv_rows)} new parameter values...")
        with db.session() as s:
            # Insert in chunks to avoid SQL limits
            chunk_size = 1000
            for i in trange(0, len(pv_rows), chunk_size):
                chunk = pv_rows[i : i + chunk_size]
                s.exec(sa_insert(BaselineParameterValueTable).values(chunk))
            s.commit()
        print(f"    Successfully added {len(pv_rows)} parameter values")

    # Migrate datasets if requested
    if include_datasets:
        if country == "uk":
            hf_repo = "policyengine/policyengine-uk-data-private"
            hf_filenames = ["enhanced_frs_2023_24.h5", "frs_2023_24.h5"]
        elif country == "us":
            hf_repo = "policyengine/policyengine-us-data"
            hf_filenames = ["enhanced_cps_2024.h5"]
        else:
            hf_repo = None
            hf_filenames = []

        if hf_repo and hf_filenames:
            migrate_datasets(db, country, hf_repo, hf_filenames)

    print(f"Migration complete for {country.upper()}!")


def migrate_datasets(
    db: Database,
    country: str,
    hf_repo: str,
    hf_filenames: list[str],
    hf_version: str = None,
) -> None:
    """Migrate datasets for a specific country.

    Args:
        db: Database instance to migrate
        country: Country code ("uk" or "us")
    """
    country = country.lower()

    print(f"Migrating {country.upper()} datasets...")

    if hf_version is None:
        versions = hf_list_tags(hf_repo)
        hf_version = versions[-1] if versions else None
        print(f"  Using latest Hugging Face version: {hf_version}")

    datasets = []

    if country == "uk":
        from policyengine.countries.uk.datasets import (
            create_dataset_years_from_hf,
        )

        # Create datasets
        for filename in hf_filenames:
            datasets.extend(
                create_dataset_years_from_hf(
                    start_year=2023,
                    end_year=2030,
                    repo=hf_repo,
                    filename=filename,
                    version=hf_version,
                )
            )

    elif country == "us":
        from policyengine.countries.us.datasets import (
            create_dataset_years_from_hf,
        )

        for hf_filename in hf_filenames:
            datasets.extend(
                create_dataset_years_from_hf(
                    start_year=2024,
                    end_year=2030,
                    repo=hf_repo,
                    filename=hf_filename,
                    version=hf_version,
                )
            )

    else:
        raise ValueError(f"Unknown country: {country}")

    # Upsert datasets to database
    if datasets:
        print(f"  Adding {len(datasets)} datasets to database...")
        db.add_all(datasets, refresh=False, chunk_size=1, progress=True)
        print(f"  Successfully migrated {len(datasets)} datasets")


def migrate_all(
    db: Database,
    countries: Iterable[str] | None = None,
    include_datasets: bool = True,
) -> None:
    """Migrate all specified countries to the database.

    Args:
        db: Database instance to migrate
        countries: List of country codes to migrate (default: ["uk", "us"])
        include_datasets: Whether to also migrate datasets (default True)
    """
    if countries is None:
        countries = ["uk", "us"]

    for country in countries:
        try:
            migrate_country(db, country, include_datasets=include_datasets)
        except ImportError as e:
            print(
                f"Warning: Could not migrate {country} - package not installed: {e}"
            )
        except Exception as e:
            print(f"Error migrating {country}: {e}")
            raise
