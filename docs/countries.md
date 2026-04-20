---
title: "Country models"
---

The `policyengine` package is country-agnostic; country-specific rules live in separate packages (`policyengine-us`, `policyengine-uk`, …). This page documents the differences that matter to users.

## Entities

| US | UK |
|---|---|
| `person` | `person` |
| `family` | — |
| `marital_unit` | — |
| `tax_unit` | `benunit` |
| `spm_unit` | — |
| `household` | `household` |

The UK `benunit` roughly corresponds to the US `tax_unit` for means-testing — a single adult or married couple plus dependent children.

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
| UK | Enhanced FRS 2024 (`enhanced_frs_2024.h5`) |

## State / regional breakdown

US: `state_code`, `congressional_district` on every record.

UK: constituency code, local authority code on every record where available.

## Poverty

US: SPM (Supplemental Poverty Measure), deep SPM (below half the threshold), plus official thresholds.

UK: AHC (After Housing Costs) and BHC (Before Housing Costs), both relative (60 % of median) and absolute.

## Key programs

| US | UK |
|---|---|
| Federal income tax (incl. EITC, CTC) | Income tax (incl. personal allowance) |
| State income taxes | — |
| Payroll taxes | National Insurance |
| SNAP | Universal Credit (absorbing legacy benefits) |
| TANF | Child Benefit |
| SSI | PIP |
| CHIP | — (NHS is universal) |
| ACA premium tax credits | — |
| Medicare Part B | — |

## Reform targeting

Parameter paths mirror the country's rule-making structure:

- US: `gov.irs.*`, `gov.states.<st>.*`, `gov.usda.*`, `gov.hhs.*`, etc.
- UK: `gov.hmrc.*`, `gov.dwp.*`, `gov.obr.*`

See [Reforms](reforms.md) for how to express changes in either tree.

## Switching countries

Most analysis patterns are identical — swap `pe.us` for `pe.uk`:

```python
# US
pe.us.calculate_household(people=[{"age": 35, "employment_income": 60_000}],
                           tax_unit={"filing_status": "SINGLE"}, year=2026)

# UK
pe.uk.calculate_household(people=[{"age": 35, "employment_income": 50_000}],
                           year=2026)
```

Microsim is similarly parallel — `pe.us.ensure_datasets` / `pe.uk.ensure_datasets`, `pe.Simulation(country="us"|"uk", ...)`.
