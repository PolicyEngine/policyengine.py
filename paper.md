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
    orcid: 0000-0002-1335-8277
    affiliation: '1'
  - name: Nikhil Woodruff
    orcid: 0009-0009-5004-4910
    affiliation: '1'
  - name: Vahid Ahmadi
    orcid: 0009-0004-1093-6272
    affiliation: '1'
    corresponding: true
  - name: Pavel Makarchuk
    orcid: 0009-0003-4869-7409
    affiliation: '1'
affiliations:
  - name: PolicyEngine, Washington, DC, United States
    index: '1'
date: 19 March 2026
bibliography: paper.bib
---

# Summary

PolicyEngine.py [@policyengine_py] is an open-source, multi-country microsimulation framework for tax-benefit policy analysis, implemented in Python. The package provides a unified interface for running policy simulations, analyzing distributional impacts, and visualizing results across the US and the UK. It delegates country-specific tax-benefit calculations to dedicated country packages (policyengine-us and policyengine-uk) while providing shared abstractions for simulations, datasets, parametric reforms, and output analysis. The framework supports both individual household simulations and population-wide microsimulations using representative survey microdata with calibrated weights. PolicyEngine powers an interactive web application at [policyengine.org](https://policyengine.org) that enables non-technical users to explore policy reforms in both countries.

# Statement of Need

Tax-benefit microsimulation models are essential tools for evaluating the distributional impacts of fiscal policy. Governments, think tanks, and researchers rely on such models to estimate how policy reforms affect household incomes, poverty rates, and government budgets. Existing microsimulation models face significant access barriers. TAXSIM [@taxsim] at NBER computes only tax liabilities and omits the benefit side of the ledger entirely. The models maintained by the Congressional Budget Office and the Tax Policy Center are fully proprietary and unavailable to external researchers. In the UK, UKMOD [@sutherland2014euromod], maintained by the University of Essex, requires a formal application and institutional affiliation to access, and the models maintained by HM Treasury and the Institute for Fiscal Studies are similarly proprietary.
PolicyEngine addresses these gaps by providing an open-source Python microsimulation framework that spans multiple countries under a consistent API. Users can supply their own microdata or use built-in datasets, and compute the impact of current law or hypothetical policy reforms on any household or a national population. The Simulation class supports individual household analysis, while population-level aggregate analysis uses representative survey datasets with calibrated weights. Because existing proprietary models cannot be independently verified, PolicyEngine enables reproducible and transparent policy analysis. The framework's open development on GitHub enables external validation, community contributions, and reproducible policy analysis across countries.

# State of the Field

The primary UK microsimulation models include UKMOD, maintained by the Institute for Social and Economic Research (ISER), University of Essex, as part of the EUROMOD family [@sutherland2014euromod], and proprietary models maintained by HM Treasury and the Institute for Fiscal Studies. OpenFisca [@openfisca] pioneered the open-source approach to tax-benefit microsimulation in France. PolicyEngine originated from OpenFisca and builds on this foundation through the PolicyEngine Core framework [@policyengine_core].

Rather than contributing these features directly to OpenFisca, PolicyEngine introduced a separate analyst-facing layer because the project required capabilities that cut across countries and sit downstream of legislative modeling: harmonized dataset handling, a stable reform API, standardized distributional outputs, and integration with a public-facing web application. This design lets country model packages focus on statutory rules while shared analysis workflows evolve independently.

PolicyEngine differentiates itself in several ways:

- **Open-source, multi-country framework**: a single Python package supports the US and UK tax-benefit systems under a consistent API, with no institutional access or license fees required.
- **Comprehensive program coverage**: the US model covers over 11 programs including federal income tax, payroll taxes, state income taxes, SNAP, SSI, Social Security, Medicare, Medicaid, EITC, CTC, and TANF; the UK model covers over 37 programs spanning income tax, National Insurance, Universal Credit, Child Benefit, Council Tax, and devolved policies in Scotland and Wales.
- **Separated modeling, analysis, and data layers**: the project splits reusable engine logic into PolicyEngine Core, country-agnostic analysis workflows into PolicyEngine.py, country legislation into policyengine-us and policyengine-uk, and enhanced survey microdata into companion repositories [@policyengine_core; @woodruff2024enhanced_cps]. This separation allows each layer to be versioned and updated independently as legislation, methodology, and microdata change.
- **Programmatic reform and economic analysis**: users can define hypothetical policy reforms as date-bound parameter values, compose multiple reforms with the `+` operator, or implement structural changes via simulation modifiers, then evaluate impacts on households, poverty, inequality, government budgets, and subnational regions. Behavioral response modules model both intensive-margin (hours adjustment) and extensive-margin (participation) labor supply responses to policy changes.

# Software Design

![PolicyEngine architecture. Three inputs — policies (tax-benefit rules and parameters from country packages), households (survey microdata with calibrated weights), and dynamics (behavioural response elasticities) — feed into the Simulation engine, which produces standardized analytical outputs including decile impacts, poverty rates, inequality metrics, regional breakdowns, and budgetary impacts.](architecture.png){width="100%"}

Figure 1 illustrates the high-level architecture. PolicyEngine is built as a four-layer system. PolicyEngine Core extends the OpenFisca engine with reusable simulation abstractions, versioned parameters, and dataset interfaces shared across countries [@policyengine_core]. PolicyEngine.py adds country-agnostic analyst workflows, including baseline-versus-reform comparisons, standardized output types, and visualization helpers. The policyengine-us and policyengine-uk packages contain statutory logic, variables, and entity structures specific to each tax-benefit system. Companion data repositories hold enhanced survey microdata and calibration pipelines for the CPS [@woodruff2024enhanced_cps] and Family Resources Survey.

This split trades some packaging complexity for clearer ownership and release independence. Legislative changes in a country package do not require duplicating shared output logic; methodological changes to distributional analysis do not require modifying statutory formulas; and microdata refreshes can be versioned separately from the modeling libraries. It also supports different contributor workflows, since legal rules, data calibration, and analyst-facing outputs are maintained by overlapping but distinct groups.

At runtime, as shown in Figure 1, a simulation combines a country model version, a microdataset, and optional reform or behavioral modifiers. PolicyEngine.py then applies a consistent analysis layer across countries, producing decile tables, poverty and inequality metrics, aggregate program statistics, and regional breakdowns from the resulting entity-level outputs. The repository documentation includes runnable examples for both household-level and population-level analyses.

PolicyEngine models static fiscal impacts; it does not model macroeconomic feedback effects or general equilibrium responses.

# Research Impact Statement

PolicyEngine has demonstrated research impact across government, academia, and policy research in both the US and UK.

**Government adoption.** In the US, PolicyEngine collaborated with the Better Government Lab — a joint center of the Georgetown McCourt School of Public Policy and the University of Michigan Ford School of Public Policy — on benefits eligibility research [@pe_bgl]. In the UK, co-author Nikhil Woodruff served as an Innovation Fellow in 2025–2026 with 10DS — the data science team at 10 Downing Street — adapting PolicyEngine for government use [@ghenis2026no10]. The 10DS team used PolicyEngine to rapidly estimate the impacts of policy reforms on living standards, local area incomes, and distributional outcomes. HM Treasury has also formally documented PolicyEngine in the UK Algorithmic Transparency Recording Standard, describing it as a model their Personal Tax, Welfare and Pensions team is exploring for "advising policymakers on the impact of tax and welfare measures on households" [@hmt2024atrs].

**Congressional and parliamentary citation.** In the US, Representatives Morgan McGarvey and Bonnie Watson Coleman cited PolicyEngine's analysis in introducing the Young Adult Tax Credit Act (H.R.7547), stating that "according to the model at PolicyEngine, 22% of all Americans would see an increase in their household income under this program, and it would lift over 4 million Americans out of poverty" [@mcgarvey2024yatc]. In the UK, Baroness Altmann referenced PolicyEngine and its interactive dashboard during House of Lords Grand Committee debate on the National Insurance Contributions (Employer Pensions Contributions) Bill in February 2026, noting that Commons Library research using PolicyEngine provided "a useful picture of the distributional effects of raising the contribution limit" across income deciles [@hansard2026nic].

**Institutional partnership.** PolicyEngine and the National Bureau of Economic Research (NBER) signed a formal memorandum of understanding for PolicyEngine to develop an open-source TAXSIM emulator — a drop-in replacement for TAXSIM-35 powered by PolicyEngine's microsimulation engine, with support for Python, R, Stata, SAS, and Julia [@pe_nber_mou]. The Federal Reserve Bank of Atlanta independently validates PolicyEngine's model through its Policy Rules Database, conducting three-way comparisons between PolicyEngine, TAXSIM, and the Fed's own models [@atlanta_fed_prd]. Co-author Max Ghenis and Jason DeBacker (University of South Carolina) presented the Enhanced Current Population Survey methodology at the 117th Annual Conference on Taxation of the National Tax Association [@ghenis2024nta].

**Academic research.** Matt Unrath (University of Southern California) is using PolicyEngine in a study of effective marginal and average tax rates facing American families, funded by the US Department of Health and Human Services through the Institute for Research on Poverty [@pe_usc]. The Beeck Center at Georgetown University featured PolicyEngine in research on rules-as-code for US public benefits [@beeck2023rac; @beeck2025ai]. Youngman et al. [@youngman2026carbon] cite PolicyEngine UK's microdata methodology in their agent-based macroeconomic model for the UK's Seventh Carbon Budget at the Institute for New Economic Thinking, Oxford.

**Policy research.** In the US, the Niskanen Center used PolicyEngine to estimate the cost and distributional impacts of Child Tax Credit reform options [@mccabe2024ctc]. DC Councilmember Zachary Parker cited PolicyEngine's analysis when introducing the District Child Tax Credit Amendment Act of 2023, the first local child tax credit in US history [@pe_dctc]. Senator Cory Booker's office embedded a PolicyEngine-built calculator on his official Senate website for the Keep Your Pay Act [@pe_keepyourpay]. In the UK, the National Institute of Economic and Social Research (NIESR) used PolicyEngine in their UK Living Standards Review 2025 [@niesr2025living], and the Institute of Economic Affairs has published PolicyEngine-based analyses of employer National Insurance contributions and 2025–2026 tax changes [@woodruff2024nic; @woodruff2025tax].

# Acknowledgements

This work was supported in the US by Arnold Ventures [@arnold_ventures], NEO Philanthropy [@neo_philanthropy], the Gerald Huff Fund for Humanity, and the National Science Foundation (NSF POSE Phase I, Award 2518372) [@nsf_pose], and in the UK by the Nuffield Foundation since September 2024 [@nuffield2024grant]. These funders had no involvement in the design, development, or content of this software or paper.

We acknowledge contributions from all PolicyEngine contributors, and thank the OpenFisca community for the foundational microsimulation framework [@openfisca]. We acknowledge the US Census Bureau for providing access to the Current Population Survey, and the UK Data Service and the Department for Work and Pensions for providing access to the Family Resources Survey. We acknowledge the UKMOD team at the Institute for Social and Economic Research (ISER), University of Essex, for their contributions to model descriptions [@sutherland2014euromod].

# AI Usage Disclosure

Generative AI tools — Claude Opus 4 by Anthropic [@claude2025] — were used to assist with code refactoring and drafting of this paper. All AI-assisted outputs were reviewed, edited, and validated by human authors, who made all core design decisions regarding software architecture, policy modeling, and parameter implementation. The authors remain fully responsible for the accuracy, originality, and correctness of all submitted materials.

# References
