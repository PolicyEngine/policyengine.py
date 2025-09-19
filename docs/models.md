# PolicyEngine model types guide

This repository contains several model types that work together to enable policy simulation and analysis. Here's what each does:

## Core simulation models

**Model** - The main computational engine that registers tax-benefit systems (UK/US) and provides the simulation function. Contains logic to create seed objects from tax-benefit parameters.

**Simulation** - Orchestrates policy analysis by combining a model, dataset, policy changes, and dynamic effects. Runs the model's simulation function and stores results.

**ModelVersion** - Tracks different versions of a model implementation, allowing for comparison across model iterations.

## Policy configuration

**Policy** - Defines policy reforms through parameter value changes. Can include a custom simulation modifier function for complex reforms.

**Dynamic** - Similar to Policy but specifically for dynamic/behavioural responses to policy changes.

**Parameter** - Represents a single policy parameter (e.g., tax rate, benefit amount) within a model.

**ParameterValue** - A specific value for a parameter at a given time period.

**BaselineParameterValue** - Default/baseline values for parameters before any policy changes.

**BaselineVariable** - Variables in the baseline scenario used for comparison.

## Data handling

**Dataset** - Contains the input data (households, people, etc.) for a simulation, with optional versioning and year specification.

**VersionedDataset** - Manages different versions of datasets over time.

## Results and reporting

**Report** - Container for analysis results with timestamp tracking.

**ReportElement** - Individual components within a report (charts, tables, metrics).

**Aggregate** - Computes aggregated statistics (sum, mean, count) from simulation results, with optional filtering.

**AggregateType** - Enum defining the available aggregation functions.

## Supporting models

**User** - User account management for the platform.

**SeedObjects** - Helper class for batch-creating initial database objects when registering a new model.