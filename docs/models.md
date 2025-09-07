# Models

We'll refer to the main classes in this package as "models". These are the main abstractions that we use to represent the key concepts in a tax-benefit microsimulation system.

These are:
* `Parameter`: A parameter represents some global variable in the tax-benefit system. For example, the personal allowance in the UK income tax system is a parameter.
* `ParameterValue`: A parameter value represents a specific value for a parameter at a given range in time (e.g. the personal allowance between April 2023 and April 2024 is £12,570).
* `Policy`: A policy represents a set of `ParameterValue`s that together define a specific change to the tax-benefit system. For example, a policy might represent a change to the personal allowance, or a change to the rate of VAT.
* `Dynamic`: A dynamic represents a set of rules that define how the tax-benefit system changes over time. For example, a dynamic might represent the annual uprating of parameters in the tax-benefit system.
* `Dataset`: A dataset represents a set of individuals and group entities (e.g. households) that we want to run the tax-benefit system on. For example, a dataset might represent the UK population in a given year.
* `Simulation`: A simulation represents the combination of a `Policy`, `Dynamic`, and `Dataset` triplet. `Simulation.run()` runs the microsimulation model with these parameters to create a new output `result` dataset.
* Output data item models: these represent essentially output 'data points' that are the result of analysing the simulation output microdata. For example, one model is `Aggregate`, which could represent 'total income tax revenue' or 'total employment income among people aged 18-24'. The full list of these models is:
  * `Aggregate`
  * `Count`
  * `ChangeByBaselineGroup`
  * `VariableChangeGroupByQuantileGroup`
