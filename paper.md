---
title: "PolicyEngine: A Tax-Benefit Microsimulation Framework"
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
  - name: Pavel Makarchuk
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Vahid Ahmadi
    orcid: 0009-0004-1093-6272
    affiliation: 1
    corresponding: true
affiliations:
  - name: PolicyEngine
    index: 1
date: 19 March 2026
bibliography: paper.bib
---

# Summary

PolicyEngine is an open-source, multi-country microsimulation framework for tax-benefit policy analysis, implemented in Python. The policyengine package provides a unified interface for running policy simulations, analyzing distributional impacts, and visualizing results across the US and the UK. It delegates country-specific tax-benefit calculations to dedicated country packages (policyengine-us and policyengine-uk) while providing shared abstractions for simulations, datasets, parametric reforms, and output analysis. The framework supports both individual household simulations and population-wide microsimulations using representative survey microdata with calibrated weights. PolicyEngine powers an interactive web application at [policyengine.org](https://policyengine.org) that enables non-technical users to explore policy reforms in both countries.

# Statement of Need

Tax-benefit microsimulation models are essential tools for evaluating the distributional impacts of fiscal policy. Governments, think tanks, and researchers rely on such models to estimate how policy reforms affect household incomes, poverty rates, and government budgets. Existing microsimulation models face significant access barriers. TAXSIM [@taxsim] at NBER computes only tax liabilities and omits the benefit side of the ledger entirely. The models maintained by the Congressional Budget Office and the Tax Policy Center are fully proprietary and unavailable to external researchers. In the UK, UKMOD [@sutherland2014euromod], maintained by the University of Essex, requires a formal application and institutional affiliation to access, and the models maintained by HM Treasury and the Institute for Fiscal Studies are similarly proprietary. None of these tools provide a unified framework for cross-country comparison.

PolicyEngine addresses these gaps by providing a fully open-source, Python microsimulation framework that spans multiple countries under a consistent API. Researchers can install the full package with pip install policyengine, or install country-specific models individually with pip install policyengine[us] or pip install policyengine[uk]. Users can supply their own microdata or use built-in datasets, and compute the impact of current law or hypothetical policy reforms on any household or a full national population. The Simulation class supports individual household analysis, while population-level aggregate analysis uses representative survey datasets with calibrated weights. The framework's open development on GitHub enables external validation, community contributions, and reproducible policy analysis across countries.

# State of the Field

In the US, TAXSIM [@taxsim] at the National Bureau of Economic Research provides tax calculations, while the Tax Policy Center and Congressional Budget Office maintain proprietary models. In the UK, the primary microsimulation models include UKMOD, maintained by the Centre for Microsimulation and Policy Analysis at the Institute for Social and Economic Research (ISER), University of Essex, as part of the EUROMOD family [@sutherland2014euromod], and models maintained internally by HM Treasury and the Institute for Fiscal Studies. OpenFisca [@openfisca] pioneered the open-source approach to tax-benefit microsimulation in France. PolicyEngine originated from OpenFisca and builds on this foundation through the PolicyEngine Core framework [@policyengine_core].

PolicyEngine differentiates itself in several ways:

- **Multi-country, open-source framework**: a single Python Python package supports the US and UK tax-benefit systems under a consistent API, with no institutional access or license fees required.
- **Comprehensive program coverage**: the US model covers over 11 programs including federal income tax, payroll taxes, state income taxes, SNAP, SSI, Social Security, Medicare, Medicaid, EITC, CTC, and TANF; the UK model covers over 37 programs spanning income tax, National Insurance, Universal Credit, Child Benefit, Council Tax, and devolved policies in Scotland and Wales.
- **Programmatic reform API**: users can define hypothetical policy reforms as parameter dictionaries with date-bound values, compose multiple reforms, or implement structural changes — and evaluate their impact on any household or the full population.
- **Economic analysis**: built-in output classes compute decile impacts, intra-decile distributions, poverty rates, inequality metrics (Gini coefficients), budgetary impacts, and regional breakdowns (US congressional districts, UK parliamentary constituencies). Behavioral response modules model both intensive margin (hours adjustment) and extensive margin (participation) labor supply responses to policy changes.

# Software Design

PolicyEngine is built on the PolicyEngine Core framework, which extends the OpenFisca microsimulation engine. The policyengine.py package is organized as a country-agnostic layer with the following core components:

**Simulation and Dataset** classes provide the primary interface. The Simulation class executes tax-benefit models on datasets, applying policy reforms and caching results. The Dataset class represents microdata containing entity-level data (persons, households, tax units) with survey weights and entity relationships. Country-specific datasets — the Current Population Survey for the US and the Enhanced Family Resources Survey for the UK — are loaded from companion data repositories [@pe_us_data; @pe_uk_data].

**Policy and Parameter** classes define the reform system. The Policy class bundles parametric reforms that modify tax-benefit system parameters. The Parameter class represents system settings (tax rates, benefit thresholds, income limits), while ParameterValue supports time-bound values, enabling phased policy implementations across multiple years.

**Variable and TaxBenefitModelVersion** classes encapsulate country-specific logic. Each Variable is a computed quantity (income tax, benefit entitlement) with entity mappings. The TaxBenefitModelVersion class represents a versioned country model, storing variables, parameters, and execution logic. The framework uses importlib to conditionally import country packages, allowing graceful operation when only one country is installed.

**Output classes** provide standardized analysis. These include Aggregate for sum, mean, and count statistics; DecileImpact and IntraDecileImpact for distributional analysis by income decile; Poverty and Inequality for welfare metrics; ChangeAggregate for baseline-versus-reform comparisons; and region-specific classes such as CongressionalDistrictImpact (US) and ConstituencyImpact (UK). All output classes produce PolicyEngine-branded Plotly visualizations.

**Region and RegionRegistry** classes manage geographic scope, enabling sub-national analysis for regions within each country.

The country-specific models (policyengine-us and policyengine-uk) define parameters as YAML files organized by government department and indexed by time period, and implement variables as Python classes specifying computation logic, entity scope, and time period. The US model covers federal and state-level tax and benefit programs and the UK model contains over 700 variable definitions.

# Research Impact Statement

PolicyEngine has demonstrated research impact across government, academia, and policy research in both the US and UK.

**Government adoption.** In the US, PolicyEngine collaborated with the Better Government Lab — a joint center of the Georgetown McCourt School of Public Policy and the University of Michigan Ford School of Public Policy — on benefits eligibility research [@pe_bgl]. In the UK, co-author Nikhil Woodruff served as an Innovation Fellow in 2025–2026 with 10DS — the data science team at 10 Downing Street — adapting PolicyEngine for government use [@ghenis2026no10]. The 10DS team used PolicyEngine to rapidly estimate the impacts of policy reforms on living standards, local area incomes, and distributional outcomes. HM Treasury has also formally documented PolicyEngine in the UK Algorithmic Transparency Recording Standard, describing it as a model their Personal Tax, Welfare and Pensions team is exploring for "advising policymakers on the impact of tax and welfare measures on households" [@hmt2024atrs].

**Congressional and parliamentary citation.** In the US, Representatives Morgan McGarvey and Bonnie Watson Coleman cited PolicyEngine's analysis in introducing the Young Adult Tax Credit Act (H.R.7547), stating that "according to the model at PolicyEngine, 22% of all Americans would see an increase in their household income under this program, and it would lift over 4 million Americans out of poverty" [@mcgarvey2024yatc]. In the UK, Baroness Altmann referenced PolicyEngine and its interactive dashboard during House of Lords Grand Committee debate on the National Insurance Contributions (Employer Pensions Contributions) Bill in February 2026, noting that Commons Library research using PolicyEngine provided "a useful picture of the distributional effects of raising the contribution limit" across income deciles [@hansard2026nic].

**Institutional partnership.** PolicyEngine and the National Bureau of Economic Research (NBER) signed a formal memorandum of understanding for PolicyEngine to develop an open-source TAXSIM emulator — a drop-in replacement for TAXSIM-35 powered by PolicyEngine's microsimulation engine, with support for Python, R, Stata, SAS, and Julia [@pe_nber_mou]. The Federal Reserve Bank of Atlanta independently validates PolicyEngine's model through its Policy Rules Database, conducting three-way comparisons between PolicyEngine, TAXSIM, and the Fed's own models [@atlanta_fed_prd]. Co-author Max Ghenis and Jason DeBacker (University of South Carolina) presented the Enhanced Current Population Survey methodology at the 117th Annual Conference on Taxation of the National Tax Association [@ghenis2024nta].

**Academic research.** In the US, Matt Unrath (University of Southern California) is using PolicyEngine in a study of effective marginal and average tax rates facing American families, funded by the US Department of Health and Human Services through the Institute for Research on Poverty [@pe_usc]. Jason DeBacker (University of South Carolina) has contributed to behavioral response modeling in PolicyEngine US with support from Arnold Ventures [@ghenis2024nta]. The Beeck Center for Social Impact and Innovation at Georgetown University featured PolicyEngine as a project spotlight in their research on rules-as-code for US public benefits programs [@beeck2023rac], and documented two Policy2Code challenge teams building on PolicyEngine in their 2025 report on AI-powered rules as code [@beeck2025ai]. In the UK, Youngman et al. [@youngman2026carbon] cite PolicyEngine UK's microdata methodology in their agent-based macroeconomic model for the UK's Seventh Carbon Budget, developed at the Institute for New Economic Thinking at Oxford in partnership with the Department for Energy Security and Net Zero.

**Policy research.** In the US, the Niskanen Center used PolicyEngine to estimate the cost and distributional impacts of Child Tax Credit reform options, becoming the first external organization to leverage PolicyEngine's enhanced US microdata [@mccabe2024ctc]. DC Councilmember Zachary Parker cited PolicyEngine's analysis when introducing the District Child Tax Credit Amendment Act of 2023, which became the first local child tax credit in US history when it passed in September 2024 [@pe_dctc]. Senator Cory Booker's office embedded a PolicyEngine-built calculator on his official Senate website for constituents to model the impact of the Keep Your Pay Act on their household taxes [@pe_keepyourpay]. In the UK, the National Institute of Economic and Social Research (NIESR) used PolicyEngine in their UK Living Standards Review 2025, acknowledging "the expertise and generosity of Nikhil Woodruff and Vahid Ahmadi in helping us maximise the benefits of using PolicyEngine" [@niesr2025living]. The Institute of Economic Affairs has published reports using PolicyEngine's microsimulation model to analyze employer National Insurance contributions [@woodruff2024nic] and the distributional impact of 2025–2026 tax changes on UK households [@woodruff2025tax].

# Acknowledgements

This work was supported in the US by Arnold Ventures [@arnold_ventures], NEO Philanthropy [@neo_philanthropy], the Gerald Huff Fund for Humanity, and the National Science Foundation (NSF POSE Phase I, Award 2518372) [@nsf_pose], and in the UK by the Nuffield Foundation since September 2024 [@nuffield2024grant]. These funders had no involvement in the design, development, or content of this software or paper.

We acknowledge contributions from all PolicyEngine contributors, and thank the OpenFisca community for the foundational microsimulation framework [@openfisca]. We acknowledge the US Census Bureau for providing access to the Current Population Survey, and the UK Data Service and the Department for Work and Pensions for providing access to the Family Resources Survey. We acknowledge the UKMOD team at the Institute for Social and Economic Research (ISER), University of Essex, for their contributions to model descriptions [@sutherland2014euromod].

# AI Usage Disclosure

Generative AI tools — Claude by Anthropic [@claude2025] — were used to assist with code refactoring and drafting of this paper. All AI-assisted outputs were reviewed, edited, and validated by human authors, who made all core design decisions regarding software architecture, policy modeling, and parameter implementation. The authors remain fully responsible for the accuracy, originality, and correctness of all submitted materials.

# References
