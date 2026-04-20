---
title: "Country models"
---

The `policyengine` package is country-agnostic; country-specific rules live in separate packages (`policyengine-us`, `policyengine-uk`). This page captures the differences that matter to users.

## Entities

| US | UK |
|---|---|
| `person` | `person` |
| `family` | — |
| `marital_unit` | — |
| `tax_unit` | `benunit` |
| `spm_unit` | — |
| `household` | `household` |

The UK `benunit` is the closest analog to the US `tax_unit` for means-testing — a single adult or married couple plus dependent children.

## Default income variable

Net-income calculations use country-specific defaults:

| | Variable |
|---|---|
| US | `spm_unit_net_income` |
| UK | `hbai_household_net_income` |

Override in any output with `income_variable=`.

## Default dataset

| | Dataset |
|---|---|
| US | Enhanced CPS 2024 (`enhanced_cps_2024.h5`) |
| UK | Enhanced FRS 2023/24 (`enhanced_frs_2023_24.h5`) |

## State / regional breakdown

US: `state_code` and `congressional_district` on every household.

UK: constituency code and local authority code on every household where available.

## Poverty

US: SPM (Supplemental Poverty Measure) and deep SPM (below half the threshold). Tracked measures are listed in `US_POVERTY_VARIABLES`.

UK: AHC (After Housing Costs) and BHC (Before Housing Costs), both relative (60 % of median) and absolute.

## Reform targeting

Parameter paths mirror the country's rule-making structure:

- US: `gov.irs.*`, `gov.states.<st>.*`, `gov.usda.*`, `gov.hhs.*`
- UK: `gov.hmrc.*`, `gov.dwp.*`, `gov.obr.*`

See [Reforms](reforms.md) for how to express changes in either tree.

## Switching countries

Most analysis patterns are identical — swap `pe.us` for `pe.uk`:

```python
# US
pe.us.calculate_household(
    people=[{"age": 35, "employment_income": 60_000}],
    tax_unit={"filing_status": "SINGLE"},
    household={"state_code": "CA"},
    year=2026,
)

# UK
pe.uk.calculate_household(
    people=[{"age": 35, "employment_income": 50_000}],
    year=2026,
)
```

Microsim is similarly parallel: `pe.us.ensure_datasets` / `pe.uk.ensure_datasets`, `Simulation(tax_benefit_model_version=pe.us.model)` / `pe.uk.model`.

## Pinned versions

Each `policyengine` release pins specific `policyengine-us` and `policyengine-uk` versions. Check them via `pe.us.model.manifest` and `pe.uk.model.manifest`. If the installed country package version diverges, the model warns — see [Release bundles](release-bundles.md).
