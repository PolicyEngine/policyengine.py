---
title: "Programs"
---

Program pages explain eligibility, benefit amounts, household-paid costs, and links to model variables. They sit between high-level methodology pages and generated variable reference pages.

A good program page should be short and structural. It should not manually reproduce every parameter table. Instead, it should explain what the program does, how the model represents it, and where generated reference pages should take over.

The migration pattern is:

| Content type | Preferred source |
|---|---|
| Narrative program explanation | Authored page in this section |
| Variable metadata, source path, entity, unit, references | Generated from country-model metadata |
| Parameter values and time series | Generated from parameter YAML |
| Data lineage and calibration targets | Generated from country data packages where possible |

## Page template

Each program page should answer:

1. Who can qualify?
2. What value does the household or person receive?
3. What costs, if any, does the household pay?
4. Which resource concepts include the benefit or cost?
5. What limitations should users know before interpreting results?

## Current US pages

- [CHIP](us-chip.md)
