"""Migration runner for updating database with latest tax-benefit model metadata and datasets."""

from typing import Iterable
from policyengine.database import Database
from policyengine.utils.metadata import get_metadata
from policyengine.utils.version import get_model_version
from policyengine.utils.hugging_face import hf_list_tags


def migrate_country(db: Database, country: str, include_datasets: bool = True) -> None:
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
        from policyengine_uk import CountryTaxBenefitSystem
        system = CountryTaxBenefitSystem()
    elif country == "us":
        from policyengine_us import CountryTaxBenefitSystem  
        system = CountryTaxBenefitSystem()
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
    
    # Migrate parameters (upsert on name, country)
    parameters = []
    for p in metadata.get("parameters", []) or []:
        p.country = country
        parameters.append(p)
    if parameters:
        print(f"  Migrating {len(parameters)} parameters...")
        db.add_all(parameters, refresh=False, chunk_size=1000, progress=True)
    
    # Migrate parameter values (upsert on parameter, model_version, country)
    pvalues = []
    for pv in metadata.get("parameter_values", []) or []:
        pv.country = country
        pv.model_version = version
        if pv.parameter is not None:
            pv.parameter.country = country
        pvalues.append(pv)
    
    if pvalues:
        # First ensure all unique parameters exist
        unique_params = {}
        for pv in pvalues:
            if pv.parameter is not None:
                key = (pv.parameter.name, pv.parameter.country)
                if key not in unique_params:
                    unique_params[key] = pv.parameter
        
        if unique_params:
            print(f"  Ensuring {len(unique_params)} parameters exist...")
            db.add_all(unique_params.values(), refresh=False, chunk_size=1000)
        
        # Then add parameter values with replacement for this model version
        print(f"  Migrating {len(pvalues)} parameter values...")
        db.add_parameter_values_bulk(
            pvalues,
            cascade=False,
            chunk_size=2000,
            progress=True,
            verbose=False,
            replace=True  # Replace existing values for this model version
        )
    
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


def migrate_datasets(db: Database, country: str, hf_repo: str, hf_filenames: list[str], hf_version: str = None) -> None:
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
        from policyengine.countries.uk.datasets import create_dataset_years_from_hf
        
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
        from policyengine.countries.us.datasets import create_dataset_years_from_hf
        
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
        db.add_all(datasets, refresh=False, chunk_size=100, progress=True)
        print(f"  Successfully migrated {len(datasets)} datasets")


def migrate_all(db: Database, countries: Iterable[str] | None = None, include_datasets: bool = True) -> None:
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
            print(f"Warning: Could not migrate {country} - package not installed: {e}")
        except Exception as e:
            print(f"Error migrating {country}: {e}")
            raise