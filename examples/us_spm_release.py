"""Run with the accompanying spm-calculator and wrapper development changes.

For an unbundled country checkout, explicitly set
POLICYENGINE_US_HOUSEHOLD_ONLY=1 before launching this script. This mode is
household-only and supplies no population certification.
"""

import json

import policyengine as pe

result = pe.us.calculate_household(
    people=[{"age": 40}, {"age": 40}, {"age": 8}, {"age": 5}],
    spm_unit={"spm_unit_tenure_type": "RENTER"},
    household={"state_code": "TX"},
    year=2025,
    spm_release=pe.us.SPMReleaseSelection(year_policy="error"),
    extra_variables=[
        "spm_unit_spm_threshold",
        "spm_unit_spm_threshold_housing_portion",
    ],
)
print(json.dumps(result.to_dict(), indent=2))
