# Ordered UK scenarios

Use `build_ordered_scenario` to preserve several module-level modifiers before and after data loading. Pass actual callables from trusted job code, with a full repository and commit claim for each occurrence. The builder returns `BoundOrderedScenario`, which exposes a native UK `Scenario`, an immutable execution plan and a live receipt identity.

```python
from policyengine.provenance import build_ordered_scenario

bound = build_ordered_scenario(
    complete_parameter_changes,
    before_modifiers=[(first_modifier, first_revision),
                      (second_modifier, second_revision)],
    after_modifiers=[(third_modifier, third_revision)],
)
simulation = NativeUKSimulation(situation=situation, scenario=bound.scenario)
reform_identity = bound.identity
```

Each revision uses `{"repository": "owner/repository", "git_sha": "<full commit SHA>"}`. The caller supplies the functions, revision claims and `NativeUKSimulation` from its trusted application. See [the runnable example](../examples/ordered_scenario.py) for a synthetic phase demonstration.

## Execution and identity

The adapter applies the complete parameter map once before loading data. It then calls every before-load modifier in order, lets the native simulation build its data, and calls every after-load modifier in order. Repeated occurrences execute repeatedly. Resolve a shared policy reference and each member's raw changes into the complete map before calling the builder; keep the application's existing member-conflict checks.

`BoundOrderedScenario.plan` stores the application order, adapter source digest, complete before-load parameters and ordered leaf proofs for both phases. Each proof records the callable's module, qualified name, source digest, module-source digest, typed module defaults and code revision. The after-load phase accepts no parameter map. The adapter and receipt identity check the same plan, and `recheck()` refuses changes to original parameters, leaf lists, revisions, defaults, loaded code or native phase fields.

Plans with modifiers use `policyengine-uk.phased_scenario_composition/v1`. Their digests cover `{"representation": ..., "payload": plan}` with RFC 8785 canonicalization and nulls retained. Parameter-only plans keep the existing before-load `scenario/v1` identity; an empty plan keeps `current_law`. Existing Scenario, phased Scenario and legacy composition digests retain their meaning. Legacy composition cannot flatten an ordered plan's phases.

## Offline verification and workers

`ordered_scenario_reform_identity(plan)` validates the closed plan and recomputes its official identity from data. It never imports, fetches or executes a module or qualified name from the payload. A source proof remains a producer's claim; applications must check approvals and provenance separately.

Workers call `bind_ordered_scenario_plan(plan, before_modifiers=..., after_modifiers=...)` with their actual trusted job callables. The binder checks each current source/default/revision proof against the complete carried plan before exposing the native scenario. Trusted `BoundOrderedScenario` objects also support pickle transport and rebind on load. Never unpickle untrusted input. JSON round-trips carry plan data; callers must rebind trusted functions before execution.

Receipt builders recheck live identities after execution. Keep the bound object that supplied `scenario`, and pass its live `identity` to the receipt builder. Loading an identity from JSON carries no live execution handle.

The [plan schema](../src/policyengine/data/schemas/ordered_scenario_plan.v1.schema.json) and [API-generated vectors](../src/policyengine/data/schemas/ordered_scenario_plan.v1.vectors.json) support offline implementations. Apply the schema's semantic rules as well as structural validation: preserve ordered typed dictionaries and repetitions, require canonical float hex values, and enforce the existing strict JSON numeric domain. Only the exact reserved `{"$nonfinite": "Infinity"}` and `{"$nonfinite": "-Infinity"}` objects encode infinite parameter values.

The API rejects arbitrary closures, dynamic modifier chains, methods, partials and dated reform objects. It does not inspect arbitrary closure cells, prove Python write sets, approve jobs or certify data. Callers retain source-based structural consistency checks and data limits.
