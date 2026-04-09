---
title: "policyengine: An Analyst Layer for Tax-Benefit Microsimulation"
tags:
  - Python
  - microsimulation
  - tax
  - benefit
  - public policy
  - economic analysis
authors:
  - name: Max Ghenis
    orcid: 0000-0002-1335-8277
    affiliation: '1'
  - name: Vahid Ahmadi
    orcid: 0009-0004-1093-6272
    affiliation: '1'
    corresponding: true
  - name: Nikhil Woodruff
    orcid: 0009-0009-5004-4910
    affiliation: '1'
  - name: Pavel Makarchuk
    orcid: 0009-0003-4869-7409
    affiliation: '1'
affiliations:
  - name: PolicyEngine, Washington, DC, United States
    index: '1'
date: 9 April 2026
bibliography: paper.bib
---

# Summary

The `policyengine` Python package [@policyengine_py] is an open-source analysis layer for tax-benefit microsimulation. It provides a common interface for running policy simulations, analyzing distributional impacts, and visualizing results across the US and the UK. It delegates country-specific tax-benefit calculations to dedicated country packages (policyengine-us and policyengine-uk) while providing shared abstractions for simulations, datasets, parametric reforms, and output analysis. The package supports both individual household simulations and population-wide microsimulations using representative survey microdata with calibrated weights. The package also powers an interactive web application at [policyengine.org](https://policyengine.org) that lets users explore policy reforms in both countries without writing code.

# Statement of Need

Tax-benefit microsimulation models are standard tools for evaluating the distributional impacts of fiscal policy. Governments, think tanks, and researchers use them to estimate how policy reforms affect household incomes, poverty rates, and government budgets. In practice, however, analysts often work across separate layers: they manage statutory rules, representative microdata, reform definitions, and distributional outputs in different tools and with different interfaces. Reproducing a baseline-versus-reform workflow, or carrying the same analysis pattern from one country model to another, therefore often requires bespoke scripts and project-specific conventions.

The `policyengine` package provides an analyst layer that works across multiple country models under a consistent API. Users can supply their own microdata or use companion representative datasets. They can then compute the impact of current law or hypothetical reforms — including parametric changes to existing policy parameters and structural modifications to the tax-benefit system — on any household or a national population. The Simulation class supports individual household analysis, while population-level aggregate analysis uses representative survey datasets with calibrated weights. The source code and development history are public on GitHub.

# State of the Field

Tax-benefit microsimulation, which Orcutt [-@orcutt1957] pioneered and Bourguignon and Spadaro [-@bourguignon2006] surveyed, underpins much of modern fiscal policy evaluation. In the US, TAXSIM [@taxsim] at the National Bureau of Economic Research provides tax calculations, while the Congressional Budget Office and Tax Policy Center maintain microsimulation tax models [@cbo2018taxmodel; @tpc2022taxmodel]. In the UK, the primary microsimulation models are UKMOD, which the Institute for Social and Economic Research (ISER) at the University of Essex maintains as part of the EUROMOD family [@sutherland2013euromod; @euromod_download_2026]; HM Treasury's Intra-Governmental Tax and Benefit Microsimulation model (IGOTM) [@hmt2025igotm]; and TAXBEN, which the Institute for Fiscal Studies maintains [@waters2017taxben].

OpenFisca [@openfisca] pioneered the open-source approach to tax-benefit microsimulation in France. Other open-source efforts include the Policy Simulation Library, a collection of policy models and data-preparation routines [@psl2026], and The Budget Lab's public US tax-model codebases, including Tax-Simulator and Cost-Recovery-Simulator [@budgetlab_taxsim_2024; @budgetlab_costrecovery_2025]. The PolicyEngine developers originally forked the codebase from OpenFisca and built it on the PolicyEngine Core framework [@policyengine_core].

The country packages already support direct microsimulation analysis and one-off weighted calculations. The `policyengine` package provides a different layer of functionality: shared dataset management, a stable baseline-versus-reform pattern, structured output types for distributional and regional analysis, and interfaces that downstream dashboards and reports use. Concretely, the package provides reusable outputs such as `Aggregate`, `ChangeAggregate`, and `IntraDecileImpact`, together with bundled analyses such as `economic_impact_analysis()`. This separation lets country model packages focus on statutory rules while shared analysis methods evolve independently.

Table 1 summarizes where `policyengine` sits relative to selected tools:

| Dimension | `policyengine` | TAXSIM | UKMOD | OpenFisca |
|---|---|---|---|---|
| Open source | Yes | Partial | Yes | Yes |
| Country coverage | US and UK | US | UK | France, with additional country packages and forks |
| Tax and benefit analysis | Yes | Tax only | Yes | Yes |
| Python package (pip install) | Yes | No | No | Yes |
| Shared reform and output API across countries | Yes | No | No | Country-specific |

The `policyengine` layer leaves reusable engine logic in PolicyEngine Core, country legislation in policyengine-us and policyengine-uk, and enhanced survey microdata in companion repositories [@policyengine_core; @woodruff2024enhanced_cps]. Teams can version and update each layer independently as legislation, methodology, and microdata change.

# Software Design

The PolicyEngine software stack has four layers. PolicyEngine Core provides reusable simulation abstractions, versioned parameters, and dataset interfaces that country packages share [@policyengine_core]. The policyengine-us and policyengine-uk packages contain statutory logic, variables, and entity structures specific to each tax-benefit system. The `policyengine` package sits above them as the analysis layer: it defines shared simulation orchestration, structured output types, and canonical baseline-versus-reform workflows such as `economic_impact_analysis()`. Companion data repositories hold enhanced survey microdata derived from the Current Population Survey (CPS) [@woodruff2024enhanced_cps] and Family Resources Survey [@frs2020]. Figure 1 illustrates the runtime workflow: inputs flow into the Simulation layer, which produces the structured outputs.

![PolicyEngine architecture. A microsimulation combines three input concepts — tax-benefit rules and parameters (policies), survey microdata (households), and behavioral responses (dynamics, defined in the country packages) — in the Simulation layer, which produces distributional impacts, fiscal impacts, regional breakdowns, poverty rates, and inequality metrics.](architecture.png){width="100%"}

The `policyengine` package centralizes distributional methods; legislative implementation remains in the country packages. The cost is coordination overhead and the need to maintain a stable interface boundary across repositories.

At runtime, a simulation combines a country model version, household microdata, and optional reform or behavioral-response inputs. The `Dynamic` class represents behavioral responses such as labor supply elasticities; the country packages define the relevant parameters, and the simulation pipeline applies them after the static policy reform. The analysis layer then produces reusable outputs for decile changes, program statistics, poverty, inequality, and regional impacts, which examples, research scripts, and the web application use.

The following example computes a household's net income under baseline law and under a reform that doubles the US standard deduction for single filers:

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
        value=30_950,
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
# Results for California: baseline net income $40,702, reform $42,484
```

A UK reproduction script that runs a population-level analysis is available at `examples/paper_repro_uk.py`.

The `policyengine` package does not include an underlying macroeconomic model in its microsimulation analysis and does not capture general equilibrium effects.

# Research Impact Statement

**Government use.** Co-author Nikhil Woodruff served as an Innovation Fellow with the 10DS data science team at 10 Downing Street, adapting PolicyEngine for government policy analysis [@no10fellowship2026]. HM Treasury documented PolicyEngine in the UK Algorithmic Transparency Recording Standard as a model their Personal Tax, Welfare and Pensions team uses [@hmt2024atrs]. The U.S. Congress Joint Economic Committee built an immigration fiscal impact calculator using PolicyEngine's microsimulation model [@jec2026immigration].

**Congressional and parliamentary citation.** In the US, members of Congress cited PolicyEngine analyses when introducing the Young Adult Tax Credit Act [@mcgarvey2024yatc], the End Child Poverty Act [@tlaib2024endchildpoverty], and the Keep Your Pay Act [@pe_keepyourpay]. In the UK, Baroness Altmann cited Commons Library research using PolicyEngine during House of Lords debate on the National Insurance Contributions (Employer Pensions Contributions) Bill [@hansard2026nic].

**Institutional use.** Under a memorandum of understanding with the Federal Reserve Bank of Atlanta, PolicyEngine runs three-way comparisons of its calculations against TAXSIM and the Atlanta Fed's Policy Rules Database [@atlanta_fed_prd]. Co-author Max Ghenis and Jason DeBacker (University of South Carolina) presented the Enhanced CPS methodology at the 117th Annual Conference on Taxation of the National Tax Association [@ghenis2024nta].

**Academic research.** The Better Government Lab (Georgetown McCourt School / University of Michigan Ford School) collaborated with PolicyEngine on benefits eligibility research [@pe_bgl]. Matt Unrath (University of Southern California) uses PolicyEngine in a study of effective marginal and average tax rates facing American families, which the US Department of Health and Human Services funds through the Institute for Research on Poverty [@pe_usc]. The Beeck Center at Georgetown University featured PolicyEngine in research on rules-as-code for US public benefits [@beeck2023rac; @beeck2025ai]. Youngman et al. [-@youngman2026carbon], at the Institute for New Economic Thinking, Oxford, cite PolicyEngine UK's microdata methodology in an agent-based macroeconomic model for the UK's Seventh Carbon Budget.

**Policy research.** In the US, the Niskanen Center used PolicyEngine to estimate the cost and distributional impacts of Child Tax Credit reform options [@mccabe2024ctc]. DC Councilmember Zachary Parker cited PolicyEngine's analysis when introducing the District Child Tax Credit Amendment Act of 2023 [@pe_dctc]. In the UK, the National Institute of Economic and Social Research (NIESR) used PolicyEngine in their UK Living Standards Review 2025 [@niesr2025living], and the Institute of Economic Affairs published PolicyEngine-based analyses of employer National Insurance contributions and 2025–2026 tax changes [@woodruff2024nic; @woodruff2025tax].

# Acknowledgements

Arnold Ventures [@arnold_ventures], NEO Philanthropy [@neo_philanthropy], the Gerald Huff Fund for Humanity, and the National Science Foundation (NSF POSE Phase I, Award 2518372) [@nsf_pose] funded this work in the US. The Nuffield Foundation has funded the UK work since September 2024 [@nuffield2024grant]. These funders had no involvement in the design, development, or content of this software or paper.

We thank all PolicyEngine contributors and the OpenFisca community for the microsimulation framework from which PolicyEngine was forked [@openfisca]. We acknowledge the US Census Bureau for providing access to the Current Population Survey, and the UK Data Service and the Department for Work and Pensions for providing access to the Family Resources Survey.

# AI Usage Disclosure

The authors used generative AI tools, specifically Claude Opus 4 by Anthropic [@claude2026], to assist with code refactoring. Human authors reviewed, edited, and validated all AI-assisted outputs and made all design decisions regarding software architecture, policy modeling, and parameter implementation. The authors remain fully responsible for the accuracy, originality, and correctness of all submitted materials.

# References
