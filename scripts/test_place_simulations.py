"""
Test script for place-level simulations.

This script tests the place-level filtering functionality by:
1. Running simulations for specific cities (NYC, Paterson NJ, Grand Rapids MI)
2. Comparing results to their parent states
3. Testing a CTC fully refundable reform
4. Checking that budgetary impact is proportional to population
5. Testing garbage/invalid inputs
"""

import sys
import traceback
from typing import Any

# =============================================================================
# Configuration
# =============================================================================

# Place definitions: (name, region_string, parent_state_region)
PLACES_TO_TEST = [
    ("New York City, NY", "place/NY-51000", "state/NY"),
    ("Paterson, NJ", "place/NJ-57000", "state/NJ"),
    ("Grand Rapids, MI", "place/MI-34000", "state/MI"),
]

# Reform: Make CTC fully refundable
CTC_FULLY_REFUNDABLE_REFORM = {
    "gov.irs.credits.ctc.refundable.fully_refundable": {
        "2024-01-01.2100-12-31": True
    }
}

# Garbage/invalid inputs to test
GARBAGE_INPUTS = [
    ("Empty place FIPS", "place/NY-"),
    ("Invalid state code", "place/XX-12345"),
    ("Non-existent place FIPS", "place/NY-99999"),
    ("Malformed region - no dash", "place/NY12345"),
    ("Malformed region - no slash", "placeNY-12345"),
    ("Wrong prefix", "city/NY-51000"),
    ("SQL injection attempt", "place/NY-51000'; DROP TABLE--"),
    ("Very long FIPS", "place/NY-" + "1" * 100),
    ("Negative FIPS", "place/NY--12345"),
    ("None as region", None),
    ("Empty string", ""),
    ("Just place/", "place/"),
    ("Lowercase state", "place/ny-51000"),
]


# =============================================================================
# Helper Functions
# =============================================================================


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_subheader(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---")


def format_currency(amount: float) -> str:
    """Format a number as currency."""
    if abs(amount) >= 1e9:
        return f"${amount/1e9:.2f}B"
    elif abs(amount) >= 1e6:
        return f"${amount/1e6:.2f}M"
    elif abs(amount) >= 1e3:
        return f"${amount/1e3:.2f}K"
    else:
        return f"${amount:.2f}"


def safe_simulation_run(
    region: str | None,
    reform: dict | None = None,
    description: str = "",
) -> dict[str, Any] | None:
    """
    Safely attempt to run a simulation, catching and reporting errors.

    Returns simulation results dict or None if failed.
    """
    from policyengine import Simulation

    try:
        options = {
            "country": "us",
            "scope": "macro",
            "time_period": "2024",
        }
        if region is not None:
            options["region"] = region
        if reform is not None:
            options["reform"] = reform

        sim = Simulation(**options)

        # Try to get basic metrics
        result = {
            "success": True,
            "region": region,
            "household_count_baseline": None,
            "total_net_income_baseline": None,
            "budgetary_impact": None,
        }

        # Get baseline household count and income
        try:
            baseline_sim = sim.baseline_simulation
            if baseline_sim is not None:
                weights = baseline_sim.calculate("household_weight").values
                result["household_count_baseline"] = weights.sum()

                net_income = baseline_sim.calculate(
                    "household_net_income", map_to="household"
                ).values
                result["total_net_income_baseline"] = (
                    net_income * weights
                ).sum()
        except Exception as e:
            result["baseline_error"] = str(e)

        # Get budgetary impact if reform was applied
        if reform is not None:
            try:
                impact = sim.calculate("budgetary/overall/budgetary_impact")
                result["budgetary_impact"] = impact
            except Exception as e:
                result["impact_error"] = str(e)

        return result

    except Exception as e:
        return {
            "success": False,
            "region": region,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }


# =============================================================================
# Test Functions
# =============================================================================


def test_place_vs_state_comparison() -> dict[str, Any]:
    """
    Test place-level simulations and compare to state-level results.

    Returns a summary of results.
    """
    print_header("Place vs State Comparison Tests")

    results = {
        "places": {},
        "states": {},
        "comparisons": {},
    }

    # First, run state-level simulations
    print_subheader("Running State-Level Baseline Simulations")
    state_regions = set(place[2] for place in PLACES_TO_TEST)

    for state_region in state_regions:
        print(f"  Running {state_region}...", end=" ", flush=True)
        result = safe_simulation_run(state_region)
        results["states"][state_region] = result
        if result and result.get("success"):
            print(
                f"OK - {result.get('household_count_baseline', 'N/A'):,.0f} households"
            )
        else:
            print(f"FAILED - {result.get('error', 'Unknown error')}")

    # Run place-level simulations
    print_subheader("Running Place-Level Baseline Simulations")

    for place_name, place_region, state_region in PLACES_TO_TEST:
        print(
            f"  Running {place_name} ({place_region})...", end=" ", flush=True
        )
        result = safe_simulation_run(place_region)
        results["places"][place_region] = result
        if result and result.get("success"):
            print(
                f"OK - {result.get('household_count_baseline', 'N/A'):,.0f} households"
            )
        else:
            print(f"FAILED - {result.get('error', 'Unknown error')}")

    # Compare place to state
    print_subheader("Place-to-State Population Ratios")

    for place_name, place_region, state_region in PLACES_TO_TEST:
        place_result = results["places"].get(place_region, {})
        state_result = results["states"].get(state_region, {})

        if (
            place_result.get("success")
            and state_result.get("success")
            and place_result.get("household_count_baseline")
            and state_result.get("household_count_baseline")
        ):

            place_hh = place_result["household_count_baseline"]
            state_hh = state_result["household_count_baseline"]
            ratio = place_hh / state_hh if state_hh > 0 else 0

            results["comparisons"][place_region] = {
                "place_households": place_hh,
                "state_households": state_hh,
                "ratio": ratio,
            }

            print(f"  {place_name}:")
            print(f"    Place households:  {place_hh:>12,.0f}")
            print(f"    State households:  {state_hh:>12,.0f}")
            print(f"    Ratio (place/state): {ratio:>10.2%}")
        else:
            print(f"  {place_name}: Could not compare (missing data)")

    return results


def test_ctc_reform_impact() -> dict[str, Any]:
    """
    Test CTC fully refundable reform impact at place and state levels.

    Checks that budgetary impact is roughly proportional to population.
    """
    print_header("CTC Fully Refundable Reform Impact Tests")

    results = {
        "places": {},
        "states": {},
        "proportionality_checks": {},
    }

    # Run state-level reform simulations
    print_subheader("Running State-Level Reform Simulations")
    state_regions = set(place[2] for place in PLACES_TO_TEST)

    for state_region in state_regions:
        print(
            f"  Running {state_region} with CTC reform...", end=" ", flush=True
        )
        result = safe_simulation_run(state_region, CTC_FULLY_REFUNDABLE_REFORM)
        results["states"][state_region] = result
        if result and result.get("success"):
            impact = result.get("budgetary_impact")
            if impact is not None:
                print(f"OK - Impact: {format_currency(impact)}")
            else:
                print(f"OK - Impact: N/A")
        else:
            print(f"FAILED - {result.get('error', 'Unknown error')}")

    # Run place-level reform simulations
    print_subheader("Running Place-Level Reform Simulations")

    for place_name, place_region, state_region in PLACES_TO_TEST:
        print(
            f"  Running {place_name} with CTC reform...", end=" ", flush=True
        )
        result = safe_simulation_run(place_region, CTC_FULLY_REFUNDABLE_REFORM)
        results["places"][place_region] = result
        if result and result.get("success"):
            impact = result.get("budgetary_impact")
            if impact is not None:
                print(f"OK - Impact: {format_currency(impact)}")
            else:
                print(f"OK - Impact: N/A")
        else:
            print(f"FAILED - {result.get('error', 'Unknown error')}")

    # Check proportionality
    print_subheader("Proportionality Check (Impact vs Population Ratio)")

    for place_name, place_region, state_region in PLACES_TO_TEST:
        place_result = results["places"].get(place_region, {})
        state_result = results["states"].get(state_region, {})

        place_impact = place_result.get("budgetary_impact")
        state_impact = state_result.get("budgetary_impact")
        place_hh = place_result.get("household_count_baseline")
        state_hh = state_result.get("household_count_baseline")

        if all(
            v is not None
            for v in [place_impact, state_impact, place_hh, state_hh]
        ):
            if state_impact != 0 and state_hh != 0:
                impact_ratio = place_impact / state_impact
                pop_ratio = place_hh / state_hh

                # Check if impact ratio is within 50% of population ratio
                # (allowing for demographic differences)
                ratio_diff = (
                    abs(impact_ratio - pop_ratio) / pop_ratio
                    if pop_ratio > 0
                    else float("inf")
                )
                is_proportional = ratio_diff < 0.5

                results["proportionality_checks"][place_region] = {
                    "place_impact": place_impact,
                    "state_impact": state_impact,
                    "impact_ratio": impact_ratio,
                    "population_ratio": pop_ratio,
                    "ratio_difference": ratio_diff,
                    "is_proportional": is_proportional,
                }

                status = "PASS" if is_proportional else "WARN"
                print(f"  {place_name}: [{status}]")
                print(f"    Impact ratio:     {impact_ratio:>10.2%}")
                print(f"    Population ratio: {pop_ratio:>10.2%}")
                print(f"    Difference:       {ratio_diff:>10.2%}")
        else:
            print(f"  {place_name}: Could not check (missing data)")

    return results


def test_garbage_inputs() -> dict[str, Any]:
    """
    Test how the system handles garbage/invalid inputs.

    This helps identify where we need more guards or type checking.
    """
    print_header("Garbage Input Tests")

    results = {
        "tests": {},
        "needs_guards": [],
    }

    for test_name, garbage_input in GARBAGE_INPUTS:
        print(f"  Testing: {test_name}", end=" ", flush=True)
        print(f"({repr(garbage_input)[:50]})")

        result = safe_simulation_run(garbage_input)
        results["tests"][test_name] = {
            "input": garbage_input,
            "result": result,
        }

        if result and result.get("success"):
            # This might indicate we need more validation
            print(f"    Result: SUCCEEDED (unexpected - may need validation)")
            results["needs_guards"].append(
                {
                    "test_name": test_name,
                    "input": garbage_input,
                    "reason": "Succeeded when it probably should have failed",
                }
            )
        else:
            error_type = (
                result.get("error_type", "Unknown") if result else "Unknown"
            )
            error_msg = (
                result.get("error", "Unknown error")
                if result
                else "Unknown error"
            )
            print(f"    Result: FAILED ({error_type})")
            print(f"    Error:  {error_msg[:100]}")

            # Check if error message is helpful
            if (
                "Traceback" in str(result.get("traceback", ""))
                and "KeyError" in error_type
            ):
                results["needs_guards"].append(
                    {
                        "test_name": test_name,
                        "input": garbage_input,
                        "reason": f"KeyError instead of descriptive error: {error_msg}",
                    }
                )

    return results


def test_datasets_functions_directly() -> dict[str, Any]:
    """
    Test the datasets.py functions directly with various inputs.
    """
    print_header("Direct Function Tests (datasets.py)")

    from policyengine.utils.data.datasets import (
        determine_us_region_type,
        parse_us_place_region,
        get_default_dataset,
    )

    results = {"tests": [], "needs_guards": []}

    # Test determine_us_region_type
    print_subheader("Testing determine_us_region_type()")

    test_cases = [
        ("place/NY-51000", "place"),
        ("place/NJ-57000", "place"),
        ("state/NY", "state"),
        ("us", "nationwide"),
        (None, "nationwide"),
        ("congressional_district/CA-01", "congressional_district"),
    ]

    for input_val, expected in test_cases:
        try:
            result = determine_us_region_type(input_val)
            status = "PASS" if result == expected else "FAIL"
            print(f"  {repr(input_val):40} -> {result:25} [{status}]")
            results["tests"].append(
                {
                    "function": "determine_us_region_type",
                    "input": input_val,
                    "result": result,
                    "expected": expected,
                    "passed": result == expected,
                }
            )
        except Exception as e:
            print(f"  {repr(input_val):40} -> ERROR: {e}")
            results["tests"].append(
                {
                    "function": "determine_us_region_type",
                    "input": input_val,
                    "error": str(e),
                    "passed": False,
                }
            )

    # Test invalid inputs for determine_us_region_type
    print_subheader("Testing determine_us_region_type() with invalid inputs")

    invalid_inputs = [
        "invalid/something",
        "place",
        "",
        "city/nyc",  # Should now fail since we removed city
    ]

    for input_val in invalid_inputs:
        try:
            result = determine_us_region_type(input_val)
            print(f"  {repr(input_val):40} -> {result} [UNEXPECTED SUCCESS]")
            results["needs_guards"].append(
                {
                    "function": "determine_us_region_type",
                    "input": input_val,
                    "reason": "Should have raised ValueError",
                }
            )
        except ValueError as e:
            print(f"  {repr(input_val):40} -> ValueError (expected) [PASS]")
        except Exception as e:
            print(f"  {repr(input_val):40} -> {type(e).__name__}: {e}")

    # Test parse_us_place_region
    print_subheader("Testing parse_us_place_region()")

    place_test_cases = [
        ("place/NY-51000", ("NY", "51000")),
        ("place/NJ-57000", ("NJ", "57000")),
        ("place/MI-34000", ("MI", "34000")),
        ("place/ca-12345", ("ca", "12345")),  # lowercase
    ]

    for input_val, expected in place_test_cases:
        try:
            result = parse_us_place_region(input_val)
            status = "PASS" if result == expected else "FAIL"
            print(f"  {repr(input_val):30} -> {result} [{status}]")
        except Exception as e:
            print(f"  {repr(input_val):30} -> ERROR: {e}")

    # Test invalid inputs for parse_us_place_region
    print_subheader("Testing parse_us_place_region() with invalid inputs")

    invalid_place_inputs = [
        "state/NY",  # Wrong prefix
        "place/NY",  # Missing FIPS
        "place/",  # Empty
        "NY-51000",  # Missing prefix
        "place/NY-",  # Empty FIPS
    ]

    for input_val in invalid_place_inputs:
        try:
            result = parse_us_place_region(input_val)
            print(f"  {repr(input_val):30} -> {result} [UNEXPECTED SUCCESS]")
            results["needs_guards"].append(
                {
                    "function": "parse_us_place_region",
                    "input": input_val,
                    "reason": f"Should have raised error, got {result}",
                }
            )
        except (ValueError, IndexError) as e:
            print(
                f"  {repr(input_val):30} -> {type(e).__name__} (expected) [PASS]"
            )
        except Exception as e:
            print(f"  {repr(input_val):30} -> {type(e).__name__}: {e}")
            results["needs_guards"].append(
                {
                    "function": "parse_us_place_region",
                    "input": input_val,
                    "reason": f"Got {type(e).__name__} instead of ValueError",
                }
            )

    return results


def print_summary(all_results: dict[str, Any]) -> None:
    """Print a summary of all test results."""
    print_header("SUMMARY")

    # Check for items needing guards
    all_needs_guards = []
    for test_name, results in all_results.items():
        if isinstance(results, dict) and "needs_guards" in results:
            for item in results["needs_guards"]:
                item["test_suite"] = test_name
                all_needs_guards.append(item)

    if all_needs_guards:
        print("\nItems that may need additional guards/validation:")
        for item in all_needs_guards:
            print(
                f"  - {item.get('test_suite', 'Unknown')}: {item.get('test_name', item.get('function', 'Unknown'))}"
            )
            print(f"    Input: {repr(item.get('input', 'N/A'))[:60]}")
            print(f"    Reason: {item.get('reason', 'N/A')}")
    else:
        print("\nNo additional guards appear to be needed.")

    print("\n" + "=" * 70)
    print(" Test script completed")
    print("=" * 70)


# =============================================================================
# Main
# =============================================================================


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" Place-Level Simulation Test Script")
    print(" Testing: NYC (NY), Paterson (NJ), Grand Rapids (MI)")
    print("=" * 70)

    all_results = {}

    # Run direct function tests first (faster, no simulation)
    all_results["direct_function_tests"] = test_datasets_functions_directly()

    # Run place vs state comparison
    all_results["place_vs_state"] = test_place_vs_state_comparison()

    # Run CTC reform tests
    all_results["ctc_reform"] = test_ctc_reform_impact()

    # Run garbage input tests
    all_results["garbage_inputs"] = test_garbage_inputs()

    # Print summary
    print_summary(all_results)

    return all_results


if __name__ == "__main__":
    results = main()
