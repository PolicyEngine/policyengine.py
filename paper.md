---
title: "policyengine: A Microsimulation Tool for Tax-Benefit Policy Analysis"
tags:
  - Python
  - microsimulation
  - tax
  - benefit
  - public policy
  - economic analysis
authors:
  - name: Vahid Ahmadi
    orcid: 0009-0004-1093-6272
    affiliation: '1'
    corresponding: true
  - name: Max Ghenis
    orcid: 0000-0002-1335-8277
    affiliation: '1'
  - name: Nikhil Woodruff
    orcid: 0009-0009-5004-4910
    affiliation: '1'
  - name: Pavel Makarchuk
    orcid: 0009-0003-4869-7409
    affiliation: '1'
affiliations:
  - name: PolicyEngine, Washington, DC, United States
    index: '1'
date: 17 April 2026
bibliography: paper.bib
---

# Summary

The `policyengine` Python package [@policyengine_py] is open-source software for analyzing how tax and benefit policies affect household incomes and government budgets in the US and UK. It gives analysts a common workflow for running simulations on representative microdata or custom households and for comparing current law with proposed reforms. Country-specific rules live in dedicated packages (`policyengine-us` and `policyengine-uk`), while `policyengine` provides shared tools for datasets, reforms, outputs, and reproducible release bundles. The package also powers the interactive web application at [policyengine.org](https://policyengine.org).

# Statement of Need

Tax-benefit microsimulation models are standard tools for evaluating the distributional impacts of fiscal policy. Governments, think tanks, and researchers use them to estimate how policy reforms affect household incomes, poverty rates, and government budgets. In practice, however, analysts work across separate components: statutory rules, representative microdata, reform definitions, and distributional outputs live in different tools and interfaces. Reproducing a baseline-versus-reform workflow, or carrying the same analysis pattern from one country model to another, therefore often requires bespoke scripts and project-specific conventions. Historical replication is especially difficult when policy rules, analysis tooling, and representative microdata are versioned independently and the analyst must reconstruct which combination produced a published estimate.

The `policyengine` package provides a consistent Python API for tax-benefit analysis across multiple country models. Users can supply their own microdata or use companion representative datasets, then compute the impact of current law or hypothetical reforms, including parametric changes to existing policy parameters and structural modifications to the tax-benefit system, on any household or a national population. The `calculate_household_impact` function computes results for a single household, while the `Simulation` class runs population-level analysis on representative survey datasets with calibrated weights. Optional behavioral-response assumptions, such as labor supply elasticities, are applied after the static reform. Version-pinned releases reduce the bookkeeping needed for replication.

# State of the Field

Microsimulation, which Orcutt [-@orcutt1957] pioneered and Bourguignon and Spadaro [-@bourguignon2006] surveyed for redistribution analysis, underpins much of modern fiscal policy evaluation. In the US, TAXSIM [@taxsim] at the National Bureau of Economic Research provides tax calculations, while the Congressional Budget Office and Tax Policy Center maintain microsimulation tax models [@cbo2018taxmodel; @tpc2022taxmodel]. In the UK, the primary microsimulation models are UKMOD, which the Institute for Social and Economic Research (ISER) at the University of Essex maintains as part of the EUROMOD family [@sutherland2013euromod; @euromod_download_2026]; HM Treasury's Intra-Governmental Tax and Benefit Microsimulation model (IGOTM) [@hmt2025igotm]; and TAXBEN, which the Institute for Fiscal Studies maintains [@waters2017taxben].

OpenFisca [@openfisca] initiated the open-source approach to tax-benefit microsimulation in France. Other open-source efforts include the Policy Simulation Library, a collection of policy models and data-preparation routines [@psl2026], and The Budget Lab's public US tax-model codebases, including Tax-Simulator and Cost-Recovery-Simulator [@budgetlab_taxsim_2024; @budgetlab_costrecovery_2025]. The PolicyEngine developers originally forked the codebase from OpenFisca and built it on the `policyengine-core` framework [@policyengine_core].

Existing tools serve complementary needs — country-specific microsimulation (TAXSIM, TAXBEN, IGOTM) or simulation infrastructure without a shared cross-country analyst API (`policyengine-core`, OpenFisca) — leaving a gap in the open-source ecosystem. The `policyengine` package fills this gap by adding shared dataset management, a stable baseline-versus-reform pattern, structured output types for distributional and regional analysis, and interfaces for downstream dashboards and reports. Concretely, the package provides reusable outputs such as `Aggregate`, `ChangeAggregate`, and `IntraDecileImpact`, together with bundled analyses such as `economic_impact_analysis()`. This separation lets country-model packages focus on statutory rules while shared analysis methods evolve independently.

Table 1: Comparison of policyengine with selected tax-benefit microsimulation tools. Entries refer to capabilities documented for external users at the time of submission.

| Dimension | policyengine | TAXSIM | UKMOD | OpenFisca |
|---|---|---|---|---|
| Open source | Yes | Partial | Yes | Yes |
| Country coverage | US and UK | US | UK | US, UK, and ~10 other jurisdictions |
| Tax and benefit analysis | Yes | Tax only | Yes | Yes |
| Python-native implementation | Yes | No | No | Yes |
| Shared reform and output API across countries | Yes | No | No | Shared core, country-specific parameters |

# Software Design

The PolicyEngine software stack has four components. `policyengine-core` provides reusable simulation abstractions, versioned parameters, and dataset interfaces that country packages share [@policyengine_core]. The `policyengine-us` and `policyengine-uk` packages contain statutory logic, variables, and entity structures specific to each tax-benefit system. The `policyengine` package is the analyst-facing component: it defines shared simulation orchestration, structured output types, and canonical baseline-versus-reform workflows such as `economic_impact_analysis()`. Companion data repositories hold enhanced survey microdata derived from the Current Population Survey (CPS) [@woodruff2024enhanced_cps] and Family Resources Survey [@frs2020]. The package does not include a macroeconomic model and does not capture general equilibrium effects.

This architecture reflects two deliberate trade-offs. Keeping country statutory rules in separate packages, rather than bundling them into a monolithic tool, lets each country model release independently; the cost is that `policyengine` must track and certify compatible combinations. Modeling reforms statically, with optional post-hoc behavioral responses, gives fast and deterministic baselines at the expense of general equilibrium effects, which are better suited to dedicated macroeconomic models.

![Figure 1: PolicyEngine runtime architecture. Inputs (rules, microdata, and behavioral responses) flow through the simulation pipeline to produce structured outputs.](architecture.png){width="100%"}

For reproducibility, the top-level package acts as a certification boundary across these components. Country data repositories build immutable microdata artifacts and publish release manifests with checksums and the country-model version used during data construction. Bundled country manifests in `policyengine` then certify the runtime bundle: the runtime country-model version, the microdata-package release, the dataset artifact, and the compatibility basis linking that runtime model to the build-time data provenance. Analysts can request a dataset such as `enhanced_frs_2023_24`, while the runtime resolves it to a specific versioned artifact and records both runtime and build-time provenance. The same certification record can be emitted as a TRACE Transparent Research Object declaration [@trace_trov], so the internal bundle and data manifests remain the operational source of truth while a standardized signed provenance document is available for external exchange.

At runtime, a simulation combines a country-model version, household microdata, and an optional reform; country packages can also apply behavioral responses, such as labor supply elasticities, after the static policy reform. The `policyengine` package then produces reusable outputs for decile changes, program statistics, poverty, inequality, and regional impacts. Because the runtime exposes the resolved certified bundle and compatibility basis, results can be traced to a specific `policyengine` release, runtime country-model release, microdata release, versioned dataset artifact, and build-time country-model version.

The following household-level example computes a household's net income under baseline law and under a reform that doubles the US single-filer standard deduction (to \$32,200 for 2026):

```python
import datetime
from policyengine.core import Parameter, ParameterValue, Policy
from policyengine.tax_benefit_models.us import (
    USHouseholdInput, calculate_household_impact, us_latest,
)

param = Parameter(
    name="gov.irs.deductions.standard.amount.SINGLE",
    tax_benefit_model_version=us_latest,
)
reform = Policy(
    name="Double standard deduction",
    parameter_values=[ParameterValue(
        parameter=param,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 31),
        value=32_200,
    )],
)

household = USHouseholdInput(
    people=[{"age": 40, "employment_income": 50_000,
             "is_tax_unit_head": True}],
    tax_unit={"filing_status": "SINGLE"},
    household={"state_code_str": "CA"},
    year=2026,
)
baseline = calculate_household_impact(household)
reformed = calculate_household_impact(household, policy=reform)
# The reform increases this household's net income relative to baseline.
```

The `us_latest` sentinel resolves to the bundled `policyengine-us` version installed alongside `policyengine`, so results are stable for a given pinned environment. This paper describes `policyengine` version 3.4.4 [@policyengine_py], and the checked-in UK reproduction script `examples/paper_repro_uk.py` documents an executable population-level workflow using a pinned interpreter (`uv run --python 3.14 --extra uk python examples/paper_repro_uk.py`).

# Research Impact Statement

PolicyEngine has seen use in government, policy, and research settings. In the UK, HM Treasury registered PolicyEngine in the Algorithmic Transparency Recording Standard as a tool under evaluation by its Personal Tax, Welfare and Pensions team [@hmt2024atrs], and co-author Nikhil Woodruff adapted PolicyEngine during an Innovation Fellowship with the data science team at 10 Downing Street [@no10fellowship2026]. In the US, the Joint Economic Committee built an immigration fiscal impact calculator on top of PolicyEngine's microsimulation model [@jec2026immigration].

The package has also been used in external policy analysis and validation exercises. Under a memorandum of understanding with the Federal Reserve Bank of Atlanta, PolicyEngine runs three-way comparisons against TAXSIM and the Atlanta Fed's Policy Rules Database [@atlanta_fed_prd]. Organizations including the Niskanen Center and the National Institute of Economic and Social Research have used PolicyEngine in published distributional analyses [@mccabe2024ctc; @niesr2025living], and co-author Max Ghenis and Jason DeBacker presented related methodology work on the Enhanced CPS at the 117th Annual Conference on Taxation of the National Tax Association [@ghenis2024nta]. Additional examples of public-facing use include research collaborations and published analyses with the Better Government Lab, the Beeck Center at Georgetown University, the Institute of Economic Affairs, and Matt Unrath at the University of Southern California [@pe_bgl; @beeck2023rac; @beeck2025ai; @woodruff2024nic; @woodruff2025tax; @pe_usc].

# Acknowledgements

Arnold Ventures [@arnold_ventures], NEO Philanthropy [@neo_philanthropy], the Gerald Huff Fund for Humanity, and the National Science Foundation (NSF POSE Phase I, Award 2518372) [@nsf_pose] funded this work in the US. The Nuffield Foundation has funded the UK work since September 2024 [@nuffield2024grant]. These funders had no involvement in the design, development, or content of this software or paper. All authors are employed by PolicyEngine and may benefit reputationally from the software's adoption; this relationship is disclosed here as a potential conflict of interest.

We thank all PolicyEngine contributors and the OpenFisca community for the microsimulation framework from which PolicyEngine was forked [@openfisca]. We acknowledge the US Census Bureau for providing access to the Current Population Survey, and the UK Data Service and the Department for Work and Pensions for providing access to the Family Resources Survey.

# AI Usage Disclosure

The authors used generative AI tools, specifically Claude Opus 4 by Anthropic [@claude2026], to assist with code refactoring. Human authors reviewed, edited, and validated all AI-assisted outputs and made all design decisions regarding software architecture, policy modeling, and parameter implementation. The authors remain fully responsible for the accuracy, originality, and correctness of all submitted materials.

# References
