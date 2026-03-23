---
title: "PolicyEngine: An Open-Source Multi-Country Tax-Benefit Microsimulation Framework"
tags:
  - Python
  - microsimulation
  - tax
  - benefit
  - public policy
  - economic analysis
authors:
  - name: Max Ghenis
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Nikhil Woodruff
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Vahid Ahmadi
    orcid: 0009-0004-1093-6272
    affiliation: 1
    corresponding: true
  - name: Pavel Makarchuk
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: PolicyEngine
    index: 1
date: 19 March 2026
bibliography: paper.bib
---

# Summary

PolicyEngine is an open-source, multi-country microsimulation framework for tax-benefit policy analysis, implemented in Python. The `policyengine` package provides a unified interface for running policy simulations, analysing distributional impacts, and visualising results across multiple countries — currently the United Kingdom and the United States. It delegates country-specific tax-benefit calculations to dedicated country packages (`policyengine-uk` and `policyengine-us`) while providing shared abstractions for simulations, datasets, parametric reforms, and output analysis. The framework supports both individual household simulations via the `Simulation` class and population-wide microsimulations using representative survey microdata with calibrated weights — the Enhanced Family Resources Survey for the UK [@pe_uk_data] and the Current Population Survey for the US [@pe_us_data]. PolicyEngine powers an interactive web application at [policyengine.org](https://policyengine.org) that enables non-technical users to explore policy reforms in both countries.

# Statement of Need

Tax-benefit microsimulation models are essential tools for evaluating the distributional impacts of fiscal policy. Governments, think tanks, and researchers rely on such models to estimate how policy reforms affect household incomes, poverty rates, and government budgets. Existing microsimulation models — such as UKMOD [@sutherland2014euromod] in the UK and TAXSIM [@taxsim] in the US — are either restricted-access, proprietary, or limited to a single country, constraining transparency, reproducibility, and cross-country comparison.

PolicyEngine addresses these gaps by providing a fully open-source, pip-installable microsimulation framework that spans multiple countries under a consistent API. Researchers can install the package with `pip install policyengine` (or selectively with `pip install policyengine[uk]` or `pip install policyengine[us]`), supply their own microdata or use built-in datasets, and compute the impact of current law or hypothetical policy reforms on any household or a full national population. The `Simulation` class supports individual household analysis, while population-level aggregate analysis uses representative survey datasets with calibrated weights. The framework's open development on GitHub enables external validation, community contributions, and reproducible policy analysis across countries.

# State of the Field

In the UK, the primary microsimulation models include UKMOD, maintained by the Centre for Microsimulation and Policy Analysis at the Institute for Social and Economic Research (ISER), University of Essex, as part of the EUROMOD family [@sutherland2014euromod], and models maintained internally by HM Treasury and the Institute for Fiscal Studies. In the US, TAXSIM [@taxsim] at the National Bureau of Economic Research provides tax calculations, while the Tax Policy Center and Congressional Budget Office maintain proprietary models. OpenFisca [@openfisca] pioneered the open-source approach to tax-benefit microsimulation in France. PolicyEngine originated from OpenFisca and builds on this foundation through the PolicyEngine Core framework [@policyengine_core].

PolicyEngine differentiates itself in several ways:

- **Multi-country, unified framework**: a single Python package supports the UK and US tax-benefit systems, enabling cross-country analysis with a consistent API.
- **Fully open-source and pip-installable**: users can install and run the model without institutional access or licence fees.
- **Comprehensive programme coverage**: the UK model covers over 37 programmes spanning income tax, National Insurance, Universal Credit, Child Benefit, Council Tax, and devolved policies in Scotland and Wales; the US model covers federal income tax, payroll taxes, SNAP, SSI, Medicaid, TANF, and state-level tax systems.
- **Integration with the PolicyEngine web application**: the models power an interactive web interface at [policyengine.org](https://policyengine.org) that allows non-technical users to explore policy reforms in both countries.
- **Programmatic reform API**: users can define hypothetical policy reforms as parameter dictionaries with date-bound values, compose multiple reforms, or implement structural changes — and evaluate their impact on any household or the full population.
- **Distributional analysis outputs**: built-in output classes compute decile impacts, intra-decile distributions, poverty rates, inequality metrics (Gini coefficients), budgetary impacts, and regional breakdowns (UK parliamentary constituencies, US congressional districts).
- **Labour supply dynamics**: behavioural response modules model both intensive margin (hours adjustment) and extensive margin (participation) responses to policy changes.

# Software Design

PolicyEngine is built on the PolicyEngine Core framework, which extends the OpenFisca microsimulation engine. The `policyengine` package is organised as a country-agnostic layer with the following core components:

**Simulation and Dataset** classes provide the primary interface. The `Simulation` class executes tax-benefit models on datasets, applying policy reforms and caching results. The `Dataset` class represents microdata containing entity-level data (persons, households, tax units) with survey weights and entity relationships. Country-specific datasets — the Enhanced Family Resources Survey for the UK and the Current Population Survey for the US — are loaded from companion data repositories [@pe_uk_data; @pe_us_data].

**Policy and Parameter** classes define the reform system. The `Policy` class bundles parametric reforms that modify tax-benefit system parameters. The `Parameter` class represents system settings (tax rates, benefit thresholds, income limits), while `ParameterValue` supports time-bound values, enabling phased policy implementations across multiple years.

**Variable and TaxBenefitModelVersion** classes encapsulate country-specific logic. Each `Variable` is a computed quantity (income tax, benefit entitlement) with entity mappings. The `TaxBenefitModelVersion` class represents a versioned country model, storing variables, parameters, and execution logic. The framework uses `importlib` to conditionally import country packages, allowing graceful operation when only one country is installed.

**Output classes** provide standardised analysis. These include `Aggregate` for sum, mean, and count statistics; `DecileImpact` and `IntraDecileImpact` for distributional analysis by income decile; `Poverty` and `Inequality` for welfare metrics; `ChangeAggregate` for baseline-versus-reform comparisons; and region-specific classes such as `ConstituencyImpact` (UK) and `CongressionalDistrictImpact` (US). All output classes produce PolicyEngine-branded Plotly visualisations.

**Region and RegionRegistry** classes manage geographic scope, enabling sub-national analysis for regions within each country.

The country-specific models (`policyengine-uk` and `policyengine-us`) define parameters as YAML files organised by government department and indexed by time period, and implement variables as Python classes specifying computation logic, entity scope, and time period. The UK model contains over 700 variable definitions and the US model covers federal and state-level tax and benefit programmes.

All code examples in the documentation are automatically re-executed with each new release to ensure correctness.

# Research Impact Statement

PolicyEngine has demonstrated research impact across government, academia, and policy research in both the UK and US.

**Government adoption.** In 2025–2026, co-author Nikhil Woodruff served as an Innovation Fellow with 10DS — the data science team at 10 Downing Street — adapting PolicyEngine for UK government use [@ghenis2026no10]. The 10DS team built `10ds-microsim` on top of PolicyEngine to rapidly estimate the impacts of policy reforms on living standards, local area incomes, and distributional outcomes. HM Treasury has also formally documented PolicyEngine in the UK Algorithmic Transparency Recording Standard, describing it as a model their Personal Tax, Welfare and Pensions team is exploring for "advising policymakers on the impact of tax and welfare measures on households" [@hmt2024atrs]. In the US, PolicyEngine collaborated with the Better Government Lab — a joint centre of the Georgetown McCourt School of Public Policy and the University of Michigan Ford School of Public Policy — on benefits eligibility research [@beeck2024rac].

**Parliamentary and congressional citation.** In February 2026, Baroness Altmann referenced PolicyEngine and its interactive dashboard during House of Lords Grand Committee debate on the National Insurance Contributions (Employer Pensions Contributions) Bill, noting that Commons Library research using PolicyEngine provided "a useful picture of the distributional effects of raising the contribution limit" across income deciles [@hansard2026nic]. In the US, Representatives Morgan McGarvey and Bonnie Watson Coleman cited PolicyEngine's analysis in introducing the Young Adult Tax Credit Act (H.R.7547), stating that "according to the model at PolicyEngine, 22% of all Americans would see an increase in their household income under this program, and it would lift over 4 million Americans out of poverty" [@mcgarvey2024yatc].

**Institutional partnership.** PolicyEngine and the National Bureau of Economic Research (NBER) signed a formal memorandum of understanding for PolicyEngine to develop an open-source TAXSIM emulator — a drop-in replacement for TAXSIM-35 powered by PolicyEngine's microsimulation engine, with support for Python, R, Stata, SAS, and Julia [@pe_nber_mou]. Co-author Max Ghenis and Jason DeBacker (University of South Carolina) presented the Enhanced Current Population Survey methodology at the 117th Annual Conference on Taxation of the National Tax Association [@ghenis2024nta].

**Academic research.** Youngman et al. [@youngman2026carbon] cite PolicyEngine's methodology in their agent-based macroeconomic model for the UK's Seventh Carbon Budget, developed at the Institute for New Economic Thinking at Oxford in partnership with the Department for Energy Security and Net Zero, noting that "the PolicyEngine microsimulation model addresses undersampling of rich households by using the Wealth and Assets Survey to impute additional wealth households into the Family Resources Survey."

**Policy research.** The National Institute of Economic and Social Research (NIESR) used PolicyEngine in their UK Living Standards Review 2025, acknowledging "the expertise and generosity of Nikhil Woodruff and Vahid Ahmadi in helping us maximise the benefits of using PolicyEngine" [@niesr2025living]. The Institute of Economic Affairs has published reports using PolicyEngine's microsimulation model to analyse employer National Insurance contributions [@woodruff2024nic] and the distributional impact of 2025–2026 tax changes on UK households [@woodruff2025tax]. In the US, the Niskanen Center used PolicyEngine to estimate the cost and distributional impacts of Child Tax Credit reform options, becoming the first external organisation to leverage PolicyEngine's enhanced US microdata [@mccabe2024ctc].

# Acknowledgements

This work was supported by the Nuffield Foundation since September 2024 [@nuffield2024grant]. The Nuffield Foundation had no involvement in the design, development, or content of this software or paper.

We acknowledge contributions from all PolicyEngine contributors, and thank the OpenFisca community for the foundational microsimulation framework [@openfisca]. We acknowledge the UKMOD team at the Institute for Social and Economic Research (ISER), University of Essex, for their contributions to model descriptions [@sutherland2014euromod]. We also acknowledge the UK Data Service and the Department for Work and Pensions for providing access to the Family Resources Survey, and the US Census Bureau for the Current Population Survey.

# AI Usage Disclosure

Generative AI tools (Claude by Anthropic, 2024–2026 [@claude2025]) were used to assist with code refactoring, test scaffolding, and drafting of this paper. All AI-assisted outputs were reviewed, edited, and validated by human authors, who made all core design decisions regarding software architecture, policy modelling, and parameter implementation. The authors remain fully responsible for the accuracy, originality, and correctness of all submitted materials.

# References
