"""Geographic utilities and constants for PolicyEngine."""

# US State FIPS codes to two-letter abbreviation mapping
STATE_FIPS_TO_ABBREV = {
    1: "AL",
    2: "AK",
    4: "AZ",
    5: "AR",
    6: "CA",
    8: "CO",
    9: "CT",
    10: "DE",
    11: "DC",
    12: "FL",
    13: "GA",
    15: "HI",
    16: "ID",
    17: "IL",
    18: "IN",
    19: "IA",
    20: "KS",
    21: "KY",
    22: "LA",
    23: "ME",
    24: "MD",
    25: "MA",
    26: "MI",
    27: "MN",
    28: "MS",
    29: "MO",
    30: "MT",
    31: "NE",
    32: "NV",
    33: "NH",
    34: "NJ",
    35: "NM",
    36: "NY",
    37: "NC",
    38: "ND",
    39: "OH",
    40: "OK",
    41: "OR",
    42: "PA",
    44: "RI",
    45: "SC",
    46: "SD",
    47: "TN",
    48: "TX",
    49: "UT",
    50: "VT",
    51: "VA",
    53: "WA",
    54: "WV",
    55: "WI",
    56: "WY",
    72: "PR",
}


def geoid_to_district_name(geoid: int) -> str:
    """Convert congressional district geoid (SSDD format) to name like 'GA-05'.

    Args:
        geoid: Congressional district geoid in SSDD format where SS is the
            state FIPS code and DD is the district number.

    Returns:
        District name in format "XX-DD" (e.g., "GA-05", "CA-12").
    """
    state_fips = geoid // 100
    district_num = geoid % 100
    state_abbrev = STATE_FIPS_TO_ABBREV.get(state_fips, f"S{state_fips}")
    return f"{state_abbrev}-{district_num:02d}"
