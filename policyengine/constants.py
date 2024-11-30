"""Mainly simulation options and parameters."""

# Datasets

ENHANCED_FRS = "hf://policyengine/policyengine-uk-data/enhanced_frs_2022_23.h5"
FRS = "hf://policyengine/policyengine-uk-data/frs_2022_23.h5"

ENHANCED_CPS = "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"
CPS = "hf://policyengine/policyengine-us-data/cps_2023.h5"
POOLED_CPS = "hf://policyengine/policyengine-us-data/pooled_3_year_cps_2023.h5"

DATASETS = {
    "uk": {"frs": FRS, "enhanced_frs": ENHANCED_FRS},
    "us": {"cps": CPS, "enhanced_cps": ENHANCED_CPS, "pooled_cps": POOLED_CPS},
}

DEFAULT_DATASETS = {
    "uk": ENHANCED_FRS,
    "us": CPS,
}
