---
title: "Model architecture"
---

PolicyEngine models tax and benefit systems as a set of country packages wrapped by the `policyengine` Python interface. The country packages contain the policy rules; this package provides the user-facing calculation and analysis surface.

This page describes the documentation structure we would choose if starting fresh.

## Three layers

PolicyEngine documentation should keep three layers separate:

| Layer | Owns | Should answer |
|---|---|---|
| Methodology | Authored prose | Why the model is structured this way, how concepts flow, where assumptions enter |
| Program pages | Authored prose plus generated links | What a program does, who qualifies, how values and household costs are represented |
| Reference | Generated from code and data packages | What variables, parameters, programs, sources, and calibration targets exist in a release |

This split avoids two common failure modes:

- Long-form methodology pages becoming stale variable catalogs.
- Generated reference pages trying to explain modeling choices that need narrative context.

## Source of truth

The source of truth should depend on content type:

| Content | Source |
|---|---|
| Formulas, entities, variable metadata | Country model packages such as `policyengine-us` |
| Parameter values, uprating, legislative references | Country model parameter YAML |
| Microdata construction, imputations, calibration targets | Country data packages such as `policyengine-us-data` |
| User tutorials, model-wide methodology, program narratives | `policyengine.py` docs |

The documentation site should not manually copy reference metadata that can be regenerated from a release. It should explain how the generated pieces fit together.

## Rules, data, calibration, outputs

A complete model page should be explicit about four pieces:

1. Rules: statutory formulas and administrative program rules.
2. Data: the household or person records to which rules are applied.
3. Calibration: adjustments that align the data and model outputs with external targets.
4. Outputs: the resource, budget, poverty, inequality, and distributional concepts returned to users.

For example, a program page should not stop at eligibility. It should say how benefit value is represented, whether household-paid costs are modeled, what data inputs are required, and how the program enters aggregate output concepts.

## Behavior inputs and legal semantics

Legal rules, population construction, and non-legal behavioral mechanics have
different owners:

| Layer | Owns |
|---|---|
| Source systems and Chronicle | Documentary source facts |
| Microcosm | Population construction and measured or latent population flags |
| PolicyEngine | Explicit population-input bindings and, in later stages, non-legal take-up and labor-supply mechanics |
| Axiom and RuleSpec | Only legal rules, concepts, events, and statuses grounded in public documents |

These terms are not interchangeable:

- **Eligibility** is a legal qualifying predicate.
- **Entitlement** is a legal right or calculated amount. It does not establish
  application, award, payment, or receipt.
- **Application or claim** is a claimant or administrative event. Microcosm may
  carry measured or latent application state; Axiom may receive it only when an
  exact public authority makes it legally operative.
- **Award** is an administrative determination. It must not be inferred from
  eligibility or receipt.
- **Payment** is a legal amount due, issued, or disbursed.
- **Receipt** is a measured or latent population fact or a PolicyEngine
  behavioral outcome. It may lag or differ from legal payment.
- **Simulated non-take-up** is a PolicyEngine-owned behavioral outcome. It is
  not ineligibility, denial, loss of entitlement, or an Axiom fact.

Eligibility or a positive static amount alone proves none of application,
award, payment, or receipt.

`BehaviorInputBinding` gives an adapter-local role an entity and column
reference. Roles are local labels, not universal legal or benefit concepts;
bindings do not contain arrays, dataframes, simulations, callables,
probabilities, or arbitrary objects. `BehaviorInputs` is the frozen,
JSON-round-trippable collection of those bindings.

The internal resolver reads only declared columns from loaded
`YearData.entity_data`. It requires a non-null, unique `<entity>_id`, copies
values into series indexed by that stable ID, and preserves nulls. It never
aligns rows positionally, remaps between entities, or requires a column to
appear in a legal-model variable registry.

This boundary only validates and resolves inputs. It adds no behavior or
Belgian formula, `takes_up_*` concept, adapter registry, legal rerun,
`Simulation` field, cache behavior, public `pe.be` export, effect on
`Simulation.run()`, or country and labor-supply numerical change.

## What belongs in generated reference

Generated reference pages should include:

- variable name, entity, period, unit, label, and documentation
- `adds`, `subtracts`, and `defined_for` relationships
- source file path and source line
- parameter value history and references
- program coverage metadata
- calibration target source, vintage, unit, and current model fit

The existing reference generator is a prototype for the variable and program parts. Parameter and data-lineage generation should follow the same pattern.

## What belongs in authored methodology

Authored methodology pages should focus on model choices:

- why a decomposition exists
- which entity owns a concept
- how gross and net quantities differ
- where a reform can change outcomes
- what is intentionally left as an imputed residual
- what current limitations users should know before interpreting outputs

That is the structure used by the first new US health-cost page.
