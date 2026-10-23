"""Backward compatibility for certified US sources without SPM declarations.

#############################################################################
# BACKWARD COMPATIBILITY — LEGACY CERTIFIED SOURCES ONLY.                    #
#                                                                            #
# policyengine-us measures SPM poverty only when a source declares two       #
# things: which SPM units are inside the SPM measurement population, and     #
# which 15–17-year-olds independently head their own SPM unit. Certified     #
# sources published before those declarations existed do not carry them,    #
# and every SPM calculation on them stops with SPM_COMPOSITION_REQUIRED.     #
#                                                                            #
# This package DERIVES the declarations from evidence those sources do       #
# carry, for the sources registered in ``registry.LEGACY_SPM_SOURCES`` and   #
# for nothing else. A new certified source is registered only for a          #
# declaration the pinned policyengine-us cannot read (today the scope,       #
# before PolicyEngine/policyengine-us#9462); see ``registry``. Otherwise new #
# certified sources must carry the declarations themselves.                  #
#                                                                            #
# ``model_adapter`` is the part that must eventually go: it overrides SPM    #
# variables only while the installed policyengine-us cannot read the scope   #
# declaration, and switches itself off once it can                           #
# (PolicyEngine/policyengine-us#9462).                                       #
#                                                                            #
# Issues: PolicyEngine/policyengine.py#597, #598. Runbook:                   #
# docs/engineering/runbooks/us-legacy-spm-sources.md                         #
#############################################################################

The pieces:

- :mod:`.registry` names each legacy source by its certified SHA-256 and the
  declarations it needs.
- :mod:`.universe` derives the SPM measurement scope (Census's ACS SPM
  methodology measures the household population, so ACS group quarters are
  outside it).
- :mod:`.independence` takes the certified SPM independence role for
  ASEC/PUF records from the national release's list.
- :mod:`.declarations` derives both for a source and writes them as the
  ordinary dataset inputs ``spm_unit_spm_universe_status`` and
  ``is_spm_independent_minor_role``, the contract that newer sources carry.
- :mod:`.record` stamps year files and outputs with the profile they were
  derived under, so that stale files are cut again and stale outputs
  recalculated.
- :mod:`.runs` decides which declarations a run needs, from a year file or
  from a raw legacy source file.
- :mod:`.model_adapter` lets a policyengine-us release that cannot read the
  scope declaration honour it.
"""

from .declarations import (
    LegacySPMDeclarations,
    add_to_year_file_frames,
    check_year_file_frames,
    derive_declarations,
    derive_from_stored_tables,
    set_declarations,
)
from .model_adapter import (
    INDEPENDENCE_ROLE,
    UNIVERSE_VARIABLE,
    ModelMode,
    prepare_microsimulation,
)
from .record import (
    ADAPTER_REVISION,
    RECORD_H5_DATASET,
    RECORD_KEY,
    LegacySPMProfile,
    LegacySPMRecord,
    expected_profile,
    parse_record,
    read_record_value,
    record_problem,
    write_record,
    year_file_problem,
)
from .registry import (
    LEGACY_SPM_SOURCES,
    IndependenceListPin,
    LegacySPMSource,
    legacy_spm_source,
)
from .runs import (
    LegacySPMRun,
    expected_profile_for_dataset,
    legacy_spm_for_run,
    raw_legacy_source,
)
from .universe import SPMUniverseStatus, classify_acs_household_population

__all__ = [
    "ADAPTER_REVISION",
    "INDEPENDENCE_ROLE",
    "LEGACY_SPM_SOURCES",
    "RECORD_H5_DATASET",
    "RECORD_KEY",
    "UNIVERSE_VARIABLE",
    "IndependenceListPin",
    "LegacySPMDeclarations",
    "LegacySPMProfile",
    "LegacySPMRecord",
    "LegacySPMRun",
    "LegacySPMSource",
    "ModelMode",
    "SPMUniverseStatus",
    "add_to_year_file_frames",
    "check_year_file_frames",
    "classify_acs_household_population",
    "derive_declarations",
    "derive_from_stored_tables",
    "expected_profile",
    "expected_profile_for_dataset",
    "legacy_spm_for_run",
    "legacy_spm_source",
    "parse_record",
    "prepare_microsimulation",
    "raw_legacy_source",
    "read_record_value",
    "record_problem",
    "set_declarations",
    "write_record",
    "year_file_problem",
]
