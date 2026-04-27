---
title: "US CHIP"
---

The Children's Health Insurance Program provides health coverage to children, and in some states pregnant people, whose household income is above Medicaid eligibility limits but within state CHIP limits.

PolicyEngine US represents CHIP as a health-coverage program with three distinct pieces: eligibility, benefit value, and household-paid premiums.

## Eligibility

`is_chip_eligible` is a person-level variable. It is true when the model determines that:

- the person is age-eligible, or eligible through a pregnancy-related CHIP pathway
- household MAGI as a share of the federal poverty line is at or below the state's CHIP income limit
- the person is not income-eligible for Medicaid
- immigration status is eligible

State eligibility thresholds are parameterized in the country model. Generated reference pages should expose the exact parameter paths, values, and legislative references by state.

## Benefit value

`per_capita_chip` represents the state's net-of-cost-sharing spending per CHIP enrollee. `per_capita_chip_gross` adds back cost-sharing offsets where available to recover a gross service-value concept.

`chip_gross` is the person-level gross value that can be summed to households or other entities.

## Premiums

`chip_premium` is the annual household-paid premium or enrollment fee at the tax-unit level. It aggregates state-specific variables because state schedules differ in structure.

The important modeling choice is not the list of states; generated reference should provide that. The authored page should explain that a premium can be:

- a household-level enrollment fee
- a per-child monthly premium
- a per-child premium with a family cap
- a premium matrix that varies by family size and income band

Those structures all produce the same tax-unit concept: an annual CHIP premium paid by the household.

## SPM and household resources

CHIP premiums are household-paid health costs. They reduce resources in concepts that include medical out-of-pocket expenses or health costs.

The decomposition is described in [US health coverage and costs](../methodology/us-health-costs.md): computed CHIP premiums are layered into reform-responsive health-cost components, while non-modeled medical spending remains in an imputed residual.

## Cost-sharing cap

Federal rules cap total CHIP cost sharing, including premiums and copays, at 5 percent of family income. The model has premium schedules, but copays are not yet modeled as a separate component. A complete cost-sharing cap requires both pieces.

## Data sources

Primary sources for premium schedules vary by state. Parameter files in `policyengine-us` cite the relevant state handbook, regulation, or Medicaid agency fee schedule where available. Cross-state surveys can be useful for discovery, but encoded parameters should prefer primary state and federal sources.

## See also

- [US health coverage and costs](../methodology/us-health-costs.md)
