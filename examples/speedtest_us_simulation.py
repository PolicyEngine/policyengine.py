"""Speedtest: US simulation performance with different dataset sizes.

This script tests how simulation.run() performance scales with dataset size
by running simulations on random subsets of households.
"""

import time
from pathlib import Path

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.tax_benefit_models.us import (
    PolicyEngineUSDataset,
    USYearData,
    us_latest,
)


def create_subset_dataset(
    original_dataset: PolicyEngineUSDataset, n_households: int
) -> PolicyEngineUSDataset:
    """Create a random subset of the dataset with n_households and reindexed entity IDs."""
    # Get original data
    household_df = pd.DataFrame(original_dataset.data.household).copy()
    person_df = pd.DataFrame(original_dataset.data.person).copy()
    marital_unit_df = pd.DataFrame(original_dataset.data.marital_unit).copy()
    family_df = pd.DataFrame(original_dataset.data.family).copy()
    spm_unit_df = pd.DataFrame(original_dataset.data.spm_unit).copy()
    tax_unit_df = pd.DataFrame(original_dataset.data.tax_unit).copy()

    # Sample random households (use n as seed to get different samples for different sizes)
    sampled_households = household_df.sample(
        n=n_households, random_state=n_households
    ).copy()
    sampled_household_ids = set(sampled_households["household_id"])

    # Determine column naming convention
    household_id_col = (
        "person_household_id"
        if "person_household_id" in person_df.columns
        else "household_id"
    )
    marital_unit_id_col = (
        "person_marital_unit_id"
        if "person_marital_unit_id" in person_df.columns
        else "marital_unit_id"
    )
    family_id_col = (
        "person_family_id"
        if "person_family_id" in person_df.columns
        else "family_id"
    )
    spm_unit_id_col = (
        "person_spm_unit_id"
        if "person_spm_unit_id" in person_df.columns
        else "spm_unit_id"
    )
    tax_unit_id_col = (
        "person_tax_unit_id"
        if "person_tax_unit_id" in person_df.columns
        else "tax_unit_id"
    )

    # Filter person table to only include people in sampled households
    sampled_person = person_df[
        person_df[household_id_col].isin(sampled_household_ids)
    ].copy()

    # Get IDs of group entities that have members in sampled households
    sampled_marital_unit_ids = set(
        sampled_person[marital_unit_id_col].unique()
    )
    sampled_family_ids = set(sampled_person[family_id_col].unique())
    sampled_spm_unit_ids = set(sampled_person[spm_unit_id_col].unique())
    sampled_tax_unit_ids = set(sampled_person[tax_unit_id_col].unique())

    # Filter group entity tables
    sampled_marital_unit = marital_unit_df[
        marital_unit_df["marital_unit_id"].isin(sampled_marital_unit_ids)
    ].copy()
    sampled_family = family_df[
        family_df["family_id"].isin(sampled_family_ids)
    ].copy()
    sampled_spm_unit = spm_unit_df[
        spm_unit_df["spm_unit_id"].isin(sampled_spm_unit_ids)
    ].copy()
    sampled_tax_unit = tax_unit_df[
        tax_unit_df["tax_unit_id"].isin(sampled_tax_unit_ids)
    ].copy()

    # Create ID mappings to reindex to contiguous integers starting from 0
    household_id_map = {
        old_id: new_id
        for new_id, old_id in enumerate(sorted(sampled_household_ids))
    }
    marital_unit_id_map = {
        old_id: new_id
        for new_id, old_id in enumerate(sorted(sampled_marital_unit_ids))
    }
    family_id_map = {
        old_id: new_id
        for new_id, old_id in enumerate(sorted(sampled_family_ids))
    }
    spm_unit_id_map = {
        old_id: new_id
        for new_id, old_id in enumerate(sorted(sampled_spm_unit_ids))
    }
    tax_unit_id_map = {
        old_id: new_id
        for new_id, old_id in enumerate(sorted(sampled_tax_unit_ids))
    }
    person_id_map = {
        old_id: new_id
        for new_id, old_id in enumerate(sorted(sampled_person["person_id"]))
    }

    # Reindex all entity IDs in household table
    sampled_households["household_id"] = sampled_households[
        "household_id"
    ].map(household_id_map)

    # Reindex all entity IDs in person table
    sampled_person["person_id"] = sampled_person["person_id"].map(
        person_id_map
    )
    sampled_person[household_id_col] = sampled_person[household_id_col].map(
        household_id_map
    )
    sampled_person[marital_unit_id_col] = sampled_person[
        marital_unit_id_col
    ].map(marital_unit_id_map)
    sampled_person[family_id_col] = sampled_person[family_id_col].map(
        family_id_map
    )
    sampled_person[spm_unit_id_col] = sampled_person[spm_unit_id_col].map(
        spm_unit_id_map
    )
    sampled_person[tax_unit_id_col] = sampled_person[tax_unit_id_col].map(
        tax_unit_id_map
    )

    # Reindex group entity tables
    sampled_marital_unit["marital_unit_id"] = sampled_marital_unit[
        "marital_unit_id"
    ].map(marital_unit_id_map)
    sampled_family["family_id"] = sampled_family["family_id"].map(
        family_id_map
    )
    sampled_spm_unit["spm_unit_id"] = sampled_spm_unit["spm_unit_id"].map(
        spm_unit_id_map
    )
    sampled_tax_unit["tax_unit_id"] = sampled_tax_unit["tax_unit_id"].map(
        tax_unit_id_map
    )

    # Sort by ID to ensure proper ordering
    sampled_households = sampled_households.sort_values(
        "household_id"
    ).reset_index(drop=True)
    sampled_person = sampled_person.sort_values("person_id").reset_index(
        drop=True
    )
    sampled_marital_unit = sampled_marital_unit.sort_values(
        "marital_unit_id"
    ).reset_index(drop=True)
    sampled_family = sampled_family.sort_values("family_id").reset_index(
        drop=True
    )
    sampled_spm_unit = sampled_spm_unit.sort_values("spm_unit_id").reset_index(
        drop=True
    )
    sampled_tax_unit = sampled_tax_unit.sort_values("tax_unit_id").reset_index(
        drop=True
    )

    # Create new dataset
    subset_dataset = PolicyEngineUSDataset(
        name=f"Subset {n_households} households",
        description=f"Random subset of {n_households} households",
        filepath=f"./data/subset_{n_households}_households.h5",
        year=original_dataset.year,
        data=USYearData(
            person=MicroDataFrame(sampled_person, weights="person_weight"),
            household=MicroDataFrame(
                sampled_households, weights="household_weight"
            ),
            marital_unit=MicroDataFrame(
                sampled_marital_unit, weights="marital_unit_weight"
            ),
            family=MicroDataFrame(sampled_family, weights="family_weight"),
            spm_unit=MicroDataFrame(
                sampled_spm_unit, weights="spm_unit_weight"
            ),
            tax_unit=MicroDataFrame(
                sampled_tax_unit, weights="tax_unit_weight"
            ),
        ),
    )

    return subset_dataset


def speedtest_simulation(dataset: PolicyEngineUSDataset) -> float:
    """Run simulation and return execution time in seconds."""
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=us_latest,
    )

    start_time = time.time()
    simulation.run()
    end_time = time.time()

    return end_time - start_time


def main():
    print("Loading full enhanced CPS dataset...")
    dataset_path = (
        Path(__file__).parent / "data" / "enhanced_cps_2024_year_2024.h5"
    )

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {dataset_path}. "
            "Run create_datasets() from policyengine.tax_benefit_models.us first."
        )

    full_dataset = PolicyEngineUSDataset(
        name="Enhanced CPS 2024",
        description="Full enhanced CPS dataset",
        filepath=str(dataset_path),
        year=2024,
    )
    full_dataset.load()

    total_households = len(full_dataset.data.household)
    print(f"Full dataset: {total_households:,} households")

    # Test different subset sizes
    test_sizes = [
        100,
        500,
        1000,
        2500,
        5000,
        10000,
        21532,
    ]  # Last is full size

    results = []

    for n_households in test_sizes:
        if n_households > total_households:
            continue

        print(f"\nTesting {n_households:,} households...")

        if n_households == total_households:
            subset = full_dataset
        else:
            subset = create_subset_dataset(full_dataset, n_households)

        n_people = len(subset.data.person)
        print(f"  {n_people:,} people in subset")

        duration = speedtest_simulation(subset)
        print(f"  Simulation completed in {duration:.2f}s")

        results.append(
            {
                "households": n_households,
                "people": n_people,
                "duration_seconds": duration,
                "households_per_second": n_households / duration,
            }
        )

    print("\n" + "=" * 60)
    print("SPEEDTEST RESULTS")
    print("=" * 60)
    print(f"{'Households':<12} {'People':<10} {'Duration':<12} {'HH/sec':<10}")
    print("-" * 60)

    for result in results:
        print(
            f"{result['households']:<12,} {result['people']:<10,} "
            f"{result['duration_seconds']:<12.2f} {result['households_per_second']:<10.1f}"
        )

    # Calculate scaling characteristics
    print("\n" + "=" * 60)
    print("SCALING ANALYSIS")
    print("=" * 60)

    if len(results) >= 2:
        # Compare first and last results
        first = results[0]
        last = results[-1]

        size_ratio = last["households"] / first["households"]
        time_ratio = last["duration_seconds"] / first["duration_seconds"]

        print(f"Dataset size increased {size_ratio:.1f}x")
        print(f"Simulation time increased {time_ratio:.1f}x")

        if time_ratio < size_ratio * 1.2:
            print("Scaling: approximately linear or better")
        elif time_ratio < size_ratio * 2:
            print("Scaling: slightly worse than linear")
        else:
            print("Scaling: significantly worse than linear")


if __name__ == "__main__":
    main()
