---
title: "Methodology"
---

This section contains authored explanations of how PolicyEngine models policy systems. It complements program pages and generated reference pages: reference pages describe variables and parameters one by one, while methodology pages explain how the pieces fit together.

## How to read this section

PolicyEngine separates three documentation layers:

| Layer | Source | Purpose |
|---|---|---|
| Tutorials | Authored examples in this repository | Show how to use `policyengine` |
| Methodology | Authored pages in this section | Explain model structure, assumptions, and decomposition choices |
| Programs | Authored pages in `programs/` | Explain eligibility, benefit value, and household-paid costs program by program |
| Reference | Generated from country-model metadata | List variables, parameters, programs, source paths, and citations |

The long-term goal is that generated pages come from the country model and data packages, while authored methodology and program pages live here with the user-facing Python package.

## Current deep dives

- [Model architecture](model-architecture.md)
- [US health coverage and costs](us-health-costs.md)

## Program pages

- [US CHIP](../programs/us-chip.md)
