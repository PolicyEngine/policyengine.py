# policyengine.py

This package aims to simplify and productionise the use of PolicyEngine's tax-benefit microsimulation models to flexibly produce useful information at scale, slotting into existing analysis pipelines while also standardising analysis.

We do this by:
* Standardising around a set of core types that let us do policy analysis in an object-oriented way
* Exemplifying this behaviour by using this package in all PolicyEngine's production applications, and analyses

## Documentation

- [Core concepts](core-concepts.md): Architecture, datasets, simulations, policies, outputs, entity mapping
- [Economic impact analysis](economic-impact-analysis.md): Full baseline-vs-reform comparison workflow
- [Advanced outputs](advanced-outputs.md): DecileImpact, Poverty, Inequality, IntraDecileImpact
- [Regions and scoping](regions-and-scoping.md): Sub-national analysis (states, constituencies, districts)
- [UK tax-benefit model](country-models-uk.md): Entities, parameters, reform examples
- [US tax-benefit model](country-models-us.md): Entities, parameters, reform examples
- [Visualisation](visualisation.md): Publication-ready charts with Plotly
- [Development](dev.md): Setup, testing, CI, architecture
