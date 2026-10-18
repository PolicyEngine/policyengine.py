# Legacy US SPM sources (backward compatibility)

> **Backward compatibility, not a data contract.** This layer exists so that
> certified US sources that cannot carry an SPM declaration can still be
> measured: sources published *before* the declarations existed, and sources
> that cannot store a declaration because the pinned policyengine-us does not
> define its variable (today `spm_unit_spm_universe_status`, before
> PolicyEngine/policyengine-us#9462). Register only the declarations a source
> lacks. Every other certified source must carry the declarations itself; do
> not register it here.

policyengine-us measures SPM poverty only when a source declares two things:

- **Measurement scope:** which SPM units are inside the SPM measurement
  population (`spm_unit_spm_universe_status`: `INCLUDED`/`OUTSIDE`, the
  contract of PolicyEngine/microcosm#977).
- **Independence role:** which 15–17-year-olds independently head their own
  SPM unit (`is_spm_independent_minor_role`).

A legacy source carries neither. Every SPM calculation on it stops with
`SPM_COMPOSITION_REQUIRED` ("SPM unit has no classified adult").

The package
[`policyengine.tax_benefit_models.us.legacy_spm`](../../../src/policyengine/tax_benefit_models/us/legacy_spm/__init__.py)
derives the missing declarations from evidence a legacy source does carry.
Nobody is dropped: memberships, weights and every ordinary tax, benefit and
income calculation are unchanged.

## Registered sources

Sources are keyed by certified SHA-256 in `legacy_spm/registry.py`.

| Source | Scope rule | Independence list |
| --- | --- | --- |
| `populace_us_2024_acs_local` Build O (`769756c3…a7ec`) | `acs_household_population` | national release `source_spm_person_independence.csv` (`22b5968d…3ce5`) |
| `populace_us_2024_acs_local` rebuilt for microcosm#1263 (`3ce781c4…8d6c`, the bundle's certified ACS-local file) | `acs_household_population` | none: the source stores `is_spm_independent_minor_role` |

### Scope rule `acs_household_population` (#597)

Census's ACS SPM methodology measures the household population only.

- ACS records with `TYPEHUGQ` 2 or 3 and the matching `RELSHIPP` (37 or 38) are
  group quarters, so their SPM units are `OUTSIDE`.
- ACS housing-unit records are `INCLUDED`.
- Records from the `asec` and `puf_tax_detail` channels are `INCLUDED`.

Age is never used. Unknown channels, missing or inconsistent evidence, and SPM
units that mix group quarters with household people all raise.

On the full Build O source, 183,206 SPM units are outside the measurement.
On the microcosm#1263 rebuild, 181,260 are: Build O's group-quarters
units less the 1,946 one-person group-quarters records of children under 15,
which the rebuild leaves out of the population until the model reads scope
natively (PolicyEngine/microcosm#1263).

### Independence list (#598)

The source's ASEC/PUF records are the same records the certified national
release carries with a source-backed independence role. The list is joined by
`person_id` and `person_spm_unit_id`, and the join must be exact:

- every ASEC/PUF person appears once, in the same SPM unit;
- the list names nobody else.

ACS people keep the model's own fallback (household head or spouse).

On Build O, exactly 28 units change: Census-built units around an independent
teen.

## How runs get the declarations

| Path | What happens |
| --- | --- |
| `create_datasets` / `ensure_datasets` | Year files store the declarations as ordinary input columns, with a `policyengine_legacy_spm_declarations` record. |
| `Simulation.run()` over a raw legacy source file | The declarations are derived in memory. The file is recognised by its evidence columns and then its SHA-256, which is hashed once per process. |
| `managed_microsimulation` | The declarations are derived from the loaded tables and set on the simulation and its branches. |

`legacy_spm.model_adapter` then makes the model honour the scope:

- **native:** policyengine-us defines `spm_unit_spm_universe_status`
  (PolicyEngine/policyengine-us#9462). The declaration is just an input, and
  nothing is overridden.
- **override:** policyengine-us 2.2.1 cannot read it. A variable-only reform:
  - adds the input;
  - wraps the installed SPM chain so that outside units never reach the
    canonical provider and every SPM outcome for them is NaN ("not measured").

  Poverty indicators become floats (1.0, 0.0 or NaN). The override wraps the
  installed formulas, with one exception: `spm_unit_income_decile` ranks
  units, so it is recalculated over measured units with the installed method.
  A contract test pins that method. The override refuses to run if the SPM
  chain no longer has the verified shape.

Poverty rates count measured people only. A group with nobody measured has a
rate of `None`, not 0.

## Staleness

The record holds a `LegacySPMProfile`: the registry entry plus
`ADAPTER_REVISION`. Checks are total and exact, like the year-file stamp:

- `ensure_datasets` cuts a year file again, and `load_datasets` refuses it, when
  its record is absent, unreadable, malformed, or from another profile.
- `Simulation.load()` refuses an output saved under a different profile.

Raise `ADAPTER_REVISION` whenever a change to derivation or the override means
existing files must be made again.

## When the model or data changes

- **policyengine-us gains native scope (#9462).**
  `test_the_installed_model_does_not_read_scope_natively_yet` fails. Check that
  the native members include `INCLUDED` and `OUTSIDE`, and confirm the native
  runs in the integration tests. Then delete the override half of
  `model_adapter` (keep the derivation) and raise `ADAPTER_REVISION`.
- **The SPM chain changes.** `test_the_override_covers_every_variable_that_depends_on_the_provider`,
  `test_the_installed_chain_has_the_verified_shape` or
  `test_the_recalculated_decile_matches_the_installed_method` fails. Re-verify
  the override against the new chain before bumping the pin.
- **A rebuilt source declares scope and role itself.** Point the bundle at it.
  Keep the Build O registry entry only while anything still reads Build O,
  then delete it.
- **A rebuilt source can store the role but not the scope.** The pinned
  policyengine-us does not define `spm_unit_spm_universe_status`, so the
  source cannot store it (Microcosm's stored-inputs gate refuses a variable
  the model does not define). Register it with its scope rule and no
  independence list, as for the microcosm#1263 rebuild. Remove the entry once
  a release of the source carries the scope natively.

## Related

- Microcosm #977: scope classification at source.
- Microcosm #959: independence role in US builds.
- policyengine-us #9462: native scope.
- policyengine.py #519: nullable SPM summaries.
- The year-file and output stamps (#590, and #593/#594 in flight). Fold this
  record into them once those land.
