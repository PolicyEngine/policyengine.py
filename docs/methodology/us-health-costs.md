---
title: "US health coverage and costs"
---

Health programs are unusual in a tax-benefit model because they often create both a benefit value and a household-paid cost. A CHIP enrollee receives health coverage, but the household may also pay a premium. A Marketplace enrollee may receive a premium tax credit, but still pay a net plan premium. The model needs to keep those concepts separate.

This page describes the current US health-cost architecture and the next pieces the documentation should expose through generated reference.

## Resource concepts

PolicyEngine uses different resource concepts for different questions:

| Concept | Purpose |
|---|---|
| Tax liability and credits | Federal and state tax calculation |
| Health benefit value | Value of public or subsidized health coverage |
| Household health costs | Household-paid health costs that should reduce resources when health benefits are counted |
| SPM medical out-of-pocket expenses | Medical expenses subtracted from Supplemental Poverty Measure resources |

Keeping these concepts separate avoids double-counting. A premium tax credit is not the same thing as a premium paid after the credit, and a public health benefit is not the same thing as the household's out-of-pocket cost.

## Current release behavior

The current pinned US model includes these health-cost pieces:

| Component | Variables | Current treatment |
|---|---|---|
| Imputed medical spending | `medical_out_of_pocket_expenses` | Person-level CPS-imputed medical spending remains available unchanged |
| Medicare Part B | `medicare_part_b_premiums`, `income_adjusted_part_b_premium` | SPM resources subtract imputed Part B and add rules-based Part B |
| CHIP premiums | `chip_premium` | Added to SPM medical out-of-pocket expenses and to `household_health_costs` |
| Medicaid premiums | `medicaid_premium` | Added to SPM medical out-of-pocket expenses |
| Marketplace net premiums | `marketplace_net_premium` | Computed as a tax-unit variable; fuller resource integration depends on the data residualization and selected-plan assumptions described below |

In the current release, `household_health_costs` is controlled by the parameter list at `gov.household.household_health_costs`; the pinned US model includes `chip_premium` in that list. The household-health-cost aggregate only affects net income when `gov.simulation.include_health_benefits_in_net_income` is enabled, so health benefits and health costs are added symmetrically.

## SPM medical out-of-pocket decomposition

The SPM-unit medical out-of-pocket variable currently follows this structure:

```text
spm_unit_medical_out_of_pocket_expenses
    = imputed medical out-of-pocket expenses
    - imputed Medicare Part B premiums
    + computed Medicare Part B premiums
    + computed CHIP premiums
    + computed Medicaid premiums
```

This keeps person-level imputed medical spending available for rules that consume it directly, while making SPM resources more responsive to reforms that change rules-based premiums.

The longer-run target is a residualized structure:

```text
resource medical costs
    = imputed residual
    + computed public-program premiums
    + computed Marketplace net premiums
```

where the imputed residual is the survey-reported medical-cost total after subtracting baseline computed premiums during data construction.

## Marketplace premiums

Marketplace modeling has three distinct quantities:

| Quantity | Meaning |
|---|---|
| `slcsp` | Gross second-lowest-cost silver plan premium, used as the PTC benchmark |
| `aca_ptc` | Premium tax credit calculated from the benchmark and required household contribution |
| `marketplace_net_premium` | Selected-plan premium paid after applying the used PTC |

The current release includes `marketplace_net_premium`, defined as the selected-plan premium proxy minus the PTC actually used. The selected-plan premium proxy is based on the SLCSP and a selected-plan-to-benchmark ratio.

Two modeling details should be documented clearly as this area evolves:

- Gross Marketplace premiums should not be gated only on PTC eligibility. A household can be ineligible for the PTC and still buy an unsubsidized Marketplace plan.
- Resource integration should avoid double-counting against CPS private-premium imputations. Marketplace premiums need data-side residualization before they can be cleanly layered into every resource concept.

Those details belong in methodology pages; the exact variable graph and parameter values belong in generated reference pages.

## Program pages

Program pages should describe how each health program enters the model:

- eligibility
- benefit value
- household-paid premiums or cost sharing
- resource and poverty treatment
- open limitations

The first program page in this structure is [US CHIP](../programs/us-chip.md).

