"""Ordered native UK execution plans and their inert, portable receipt payloads.

Only trusted job definitions supply callables. A JSON plan never resolves a
module or qualified name, and cannot grant permission to execute Python.
"""

from __future__ import annotations

import ast
import inspect
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from types import CodeType
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

from policyengine.provenance.bytecode import code_shape
from policyengine.provenance.canonical import canonical_sha256
from policyengine.provenance.receipt import (
    SHA256_PATTERN,
    ReceiptError,
    ReformIdentity,
    _modifier_identity,
    _payload_sha256,
    _sha256_text,
    _strict_json_value,
    _typed_value,
    strict_json_value,
)

ORDERED_SCENARIO_REPRESENTATION = "policyengine-uk.phased_scenario_composition/v1"
ORDERED_SCENARIO_APPLICATION = "before_data_load_then_after_data_load"


def _immutable(*args, **kwargs):
    raise TypeError("An ordered plan is immutable; build a new plan.")


class _FrozenDict(dict):
    """JSON-shaped read-only values; low-level Python mutation is not a sandbox."""

    def __init__(self, value=()):
        dict.__init__(self, ((key, _freeze(item)) for key, item in dict(value).items()))

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable
    __ior__ = _immutable

    def __reduce__(self):
        return _FrozenDict, (dict(self),)


def _freeze(value):
    if isinstance(value, Mapping):
        return _FrozenDict(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value


def _same_content(first, second):
    """Compare JSON content: distinguish true/1 and equate numeric1/1.0."""
    return canonical_sha256(_plain(first)) == canonical_sha256(_plain(second))


class _PlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ModifierCodeRevision(_PlanModel):
    """The same full repository/commit claim accepted by the Scenario binder."""

    repository: str = Field(min_length=1)
    git_sha: str = Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def _literal(encoded):
    """Validate the existing lossless default-argument encoding, without code."""
    if not isinstance(encoded, Mapping):
        raise ReceiptError("A typed default must be an object.")
    kind = encoded.get("type")
    if kind == "none" and set(encoded) == {"type"}:
        return None
    if kind in ("bool", "int", "str") and set(encoded) == {"type", "value"}:
        expected = {"bool": bool, "int": int, "str": str}[kind]
        if type(encoded["value"]) is expected:
            return encoded["value"]
    if kind == "float" and set(encoded) == {"type", "hex"}:
        if type(encoded["hex"]) is str:
            try:
                value = float.fromhex(encoded["hex"])
            except ValueError:
                pass
            else:
                if not math.isnan(value) and value.hex() == encoded["hex"]:
                    return value
    if kind in ("list", "tuple", "dict") and set(encoded) == {"type", "items"}:
        items = encoded["items"]
        if isinstance(items, tuple | list):
            if kind != "dict":
                values = [_literal(item) for item in items]
                return tuple(values) if kind == "tuple" else values
            result = {}
            for pair in items:
                if not isinstance(pair, tuple | list) or len(pair) != 2:
                    raise ReceiptError("A typed dictionary needs key/value pairs.")
                key, item = pair
                if type(key) is not str or key in result:
                    raise ReceiptError("Typed dictionary keys must be unique strings.")
                result[key] = _literal(item)
            return result
    raise ReceiptError("Invalid typed default encoding.")


class ModifierLeafIdentity(_PlanModel):
    """Inert provenance for one occurrence of an actual module-level modifier."""

    module: str = Field(pattern=r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
    qualname: str = Field(pattern=r"^[A-Za-z_]\w*$")
    source_sha256: str = Field(pattern=SHA256_PATTERN)
    module_source_sha256: str = Field(pattern=SHA256_PATTERN)
    module_defaults: dict[str, Any] | None
    code_revision: ModifierCodeRevision

    @field_validator("module_defaults")
    @classmethod
    def _defaults(cls, value):
        if value is not None:
            if not value:
                raise ReceiptError("Empty module defaults must be null.")
            for name, encoded in value.items():
                if not name or _typed_value(_literal(encoded)) != encoded:
                    raise ReceiptError("Invalid module-default proof.")
            return _FrozenDict(value)
        return value


def _parameter_values(changes, *, encoded):
    """Closed native scalar/period-map input; infinities have a reserved encoding."""
    if not isinstance(changes, Mapping):
        raise ReceiptError("parameter_changes must be an object.")
    result = (
        strict_json_value(changes)
        if encoded
        else _strict_json_value(changes, "$.parameter_changes", nonfinite=True)
    )

    def scalar(value):
        if type(value) in (bool, int, float):
            return True
        return (
            isinstance(value, Mapping)
            and set(value) == {"$nonfinite"}
            and value["$nonfinite"] in ("Infinity", "-Infinity")
        )

    for path, value in result.items():
        if not path or path == "$nonfinite":
            raise ReceiptError("A parameter path must be nonempty and not reserved.")
        if scalar(value):
            continue
        if not isinstance(value, Mapping) or any(
            not key or key == "$nonfinite" or not scalar(item)
            for key, item in value.items()
        ):
            raise ReceiptError(
                "Native parameter values must be numeric/bool scalars or period maps."
            )
    # Enforce RFC8785's numeric domain now, not only when a digest is requested.
    canonical_sha256(result)
    return result


def _native_parameters(changes):
    def decode(value):
        if isinstance(value, Mapping):
            if set(value) == {"$nonfinite"}:
                return math.inf if value["$nonfinite"] == "Infinity" else -math.inf
            return {key: decode(item) for key, item in value.items()}
        return value

    return decode(changes)


class OrderedScenarioPhase(_PlanModel):
    """The complete parameter map and ordered modifier occurrences of one phase."""

    parameter_changes: dict[str, Any]
    modifier_leaves: tuple[ModifierLeafIdentity, ...]

    @field_validator("parameter_changes")
    @classmethod
    def _parameters(cls, value):
        return _FrozenDict(_parameter_values(value, encoded=True))

    @field_validator("modifier_leaves", mode="before")
    @classmethod
    def _leaves(cls, value):
        if not isinstance(value, list | tuple):
            raise ReceiptError("Modifier leaves must be an ordered list.")
        return tuple(value)


class OrderedScenarioPlan(_PlanModel):
    """An immutable JSON execution recipe; reading one executes no locators."""

    application: Literal["before_data_load_then_after_data_load"]
    adapter_source_sha256: str = Field(pattern=SHA256_PATTERN)
    before: OrderedScenarioPhase
    after: OrderedScenarioPhase

    @field_validator("after")
    @classmethod
    def _no_after_parameters(cls, value):
        if value.parameter_changes:
            raise ReceiptError(
                "Ordered plans apply all parameters before data loading, once."
            )
        return value

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        """Publish the closed wire schema, including native parameter shapes.

        Canonical hexadecimal floats/defaults and RFC8785 numeric-domain
        checks remain the explicit semantic rules beside the schema.
        """
        schema = cls.model_json_schema()
        scalar = {
            "anyOf": [
                {"type": "boolean"},
                {"type": "number"},
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["$nonfinite"],
                    "properties": {"$nonfinite": {"enum": ["Infinity", "-Infinity"]}},
                },
            ]
        }
        parameters = {
            "type": "object",
            "propertyNames": {"minLength": 1, "not": {"const": "$nonfinite"}},
            "additionalProperties": {
                "anyOf": [
                    scalar,
                    {
                        "type": "object",
                        "propertyNames": {
                            "minLength": 1,
                            "not": {"const": "$nonfinite"},
                        },
                        "additionalProperties": scalar,
                    },
                ]
            },
        }
        schema["$defs"]["OrderedScenarioPhase"]["properties"]["parameter_changes"] = (
            parameters
        )
        schema["properties"]["after"] = {
            "allOf": [
                {"$ref": "#/$defs/OrderedScenarioPhase"},
                {"properties": {"parameter_changes": {"const": {}}}},
            ]
        }
        typed = []
        for kind, field, shape in (
            ("none", None, None),
            ("bool", "value", {"type": "boolean"}),
            (
                "int",
                "value",
                {"type": "integer", "minimum": -(2**53 - 1), "maximum": 2**53 - 1},
            ),
            ("str", "value", {"type": "string"}),
            (
                "float",
                "hex",
                {
                    "type": "string",
                    "pattern": r"^(?:-?inf|-?0x[0-9a-f]+\.[0-9a-f]+p[+-][0-9]+)$",
                },
            ),
            (
                "list",
                "items",
                {"type": "array", "items": {"$ref": "#/$defs/TypedDefault"}},
            ),
            (
                "tuple",
                "items",
                {"type": "array", "items": {"$ref": "#/$defs/TypedDefault"}},
            ),
            (
                "dict",
                "items",
                {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "prefixItems": [
                            {"type": "string"},
                            {"$ref": "#/$defs/TypedDefault"},
                        ],
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
            ),
        ):
            properties = {"type": {"const": kind}}
            if field:
                properties[field] = shape
            typed.append(
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": properties,
                    "required": list(properties),
                }
            )
        schema["$defs"]["TypedDefault"] = {"oneOf": typed}
        schema["$defs"]["ModifierLeafIdentity"]["properties"]["module_defaults"] = {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "minProperties": 1,
                    "propertyNames": {"minLength": 1},
                    "additionalProperties": {"$ref": "#/$defs/TypedDefault"},
                },
            ]
        }
        schema["$id"] = (
            "https://policyengine.org/schemas/ordered_scenario_plan.v1.schema.json"
        )
        schema["x-policyengine-rules"] = [
            "Canonicalization is RFC8785 with nulls retained; no locator is imported or executed.",
            "Default float hex strings must equal float.fromhex(value).hex(); typed dictionary keys are unique and ordered.",
            "Apply existing strict JSON/RFC8785 numeric-domain checks; JSON NaN and numeric Infinity are invalid. Only exact reserved objects encode parameter infinities.",
            "Offline provenance is an assertion, not permission to execute. Rebind trusted actual leaf callables and compare the complete plan before runtime.",
        ]
        return schema


def _validated_plan(plan):
    if isinstance(plan, OrderedScenarioPlan):
        # Revalidate even an instance constructed/copied past Pydantic's rules.
        plan = plan.model_dump(mode="json")
    try:
        return OrderedScenarioPlan.model_validate(plan)
    except ValueError as exc:
        raise ReceiptError(f"Invalid ordered Scenario plan: {exc}") from exc


def ordered_scenario_reform_identity(
    plan: OrderedScenarioPlan | Mapping[str, Any], *, name: str | None = None
) -> ReformIdentity:
    """Recompose the official identity from closed data, without importing leaves.

    This validates provenance's form, not its truth or approval. A producer or
    worker must additionally bind its actual trusted callables with
    :func:`bind_ordered_scenario_plan` before execution.
    """
    plan = _validated_plan(plan)
    if not plan.before.modifier_leaves and not plan.after.modifier_leaves:
        changes = _native_parameters(plan.before.parameter_changes)
        if not changes:
            return ReformIdentity(kind="current_law", name=name)
        return ReformIdentity(
            kind="reform",
            representation="policyengine-uk.scenario/v1",
            reform_sha256=_payload_sha256(
                {
                    "representation": "policyengine-uk.scenario/v1",
                    "payload": {
                        "applied_before_data_load": True,
                        "parameter_changes": changes,
                        "simulation_modifier": None,
                    },
                }
            ),
            name=name,
        )
    return ReformIdentity(
        kind="reform",
        representation=ORDERED_SCENARIO_REPRESENTATION,
        reform_sha256=canonical_sha256(
            {
                "representation": ORDERED_SCENARIO_REPRESENTATION,
                "payload": plan.model_dump(mode="json"),
            }
        ),
        binding="code_revision",
        name=name,
    )


def _codes(code):
    result = {code.co_qualname: code}
    for child in code.co_consts:
        if isinstance(child, CodeType):
            # Python 3.14 emits annotation helpers beside the callable, with
            # no corresponding module/class attribute at this qualified name.
            # The existing leaf binder checks modifier annotations separately.
            if child.co_name == "__annotate__":
                continue
            result.update(_codes(child))
    return result


def _adapter_digest():
    """Bind the reviewed adapter source and reject changed loaded implementations."""
    module = sys.modules[__name__]
    source = inspect.getsource(module)
    compiled = _codes(compile(source, __file__, "exec", dont_inherit=True))
    class_bodies = {
        node.name for node in ast.parse(source).body if isinstance(node, ast.ClassDef)
    }
    for name, expected in _ADAPTER_BINDINGS.items():
        if vars(module).get(name) is not expected:
            raise ReceiptError(f"Ordered adapter binding {name} changed after import.")
    for qualname, expected in compiled.items():
        if qualname == "<module>" or "<" in qualname:
            continue
        loaded = module
        for part in qualname.split("."):
            loaded = getattr(loaded, part, None)
        if qualname in class_bodies:
            if not inspect.isclass(loaded):
                raise ReceiptError(f"Ordered adapter class {qualname} changed.")
            continue
        if isinstance(loaded, property):
            loaded = loaded.fget
        if inspect.ismethod(loaded):
            loaded = loaded.__func__
        if not inspect.isfunction(loaded):
            raise ReceiptError(f"Ordered adapter implementation {qualname} changed.")
        if code_shape(loaded.__code__) != code_shape(expected):
            raise ReceiptError(
                f"Ordered adapter code {qualname} no longer matches source."
            )
    return _sha256_text(source)


def _specs(value):
    if isinstance(value, str | bytes | Mapping) or not isinstance(value, Sequence):
        raise ReceiptError(
            "Modifiers must be an ordered sequence of (callable, revision) pairs."
        )
    result = []
    for pair in value:
        if not isinstance(pair, tuple | list) or len(pair) != 2:
            raise ReceiptError(
                "Each modifier needs its actual callable and code revision."
            )
        function, revision = pair
        try:
            checked = ModifierCodeRevision.model_validate(revision)
        except ValueError as exc:
            raise ReceiptError(f"Invalid modifier code revision: {exc}") from exc
        proof = _modifier_identity(function, checked.model_dump())
        result.append((function, revision, ModifierLeafIdentity.model_validate(proof)))
    return tuple(result)


def _make_plan(parameters, before, after):
    early = _specs(before)
    late = _specs(after)
    plan = OrderedScenarioPlan(
        application=ORDERED_SCENARIO_APPLICATION,
        adapter_source_sha256=_adapter_digest(),
        before=OrderedScenarioPhase(
            parameter_changes=_parameter_values(parameters, encoded=False),
            modifier_leaves=tuple(item[2] for item in early),
        ),
        after=OrderedScenarioPhase(
            parameter_changes={}, modifier_leaves=tuple(item[2] for item in late)
        ),
    )
    return plan, early, late


class _OrderedModifier:
    def __init__(self, owner, phase):
        self.owner = owner
        self.phase = phase

    def __call__(self, simulation):
        self.owner.recheck()
        leaves = self.owner._before if self.phase == "before" else self.owner._after
        for function, revision, proof in leaves:
            function(simulation)
            self.owner.recheck()


class BoundOrderedScenario(_PlanModel):
    """A JSON plan with process-local trusted execution and live rechecks.

    JSON round-trips the plan only. Rebind trusted job leaves after loading
    JSON. Pickle transport is supported only for trusted job objects; unpickle
    revalidates actual callable sources against the carried plan.
    """

    plan: OrderedScenarioPlan
    name: str | None = None
    _parameter_source: Any = PrivateAttr(default=None)
    _before_source: Any = PrivateAttr(default=None)
    _after_source: Any = PrivateAttr(default=None)
    _before: Any = PrivateAttr(default=None)
    _after: Any = PrivateAttr(default=None)
    _scenario: Any = PrivateAttr(default=None)
    _adapters: Any = PrivateAttr(default=None)
    _native_parts: Any = PrivateAttr(default=None)

    def _validate_live(self):
        from policyengine_uk.utils.scenario import Scenario

        if self._scenario is None:
            raise ReceiptError(
                "A data-only plan cannot execute; rebind trusted modifiers first."
            )
        live, before, after = _make_plan(
            self._parameter_source, self._before_source, self._after_source
        )
        if not _same_content(
            live.model_dump(mode="json"),
            _validated_plan(self.plan).model_dump(mode="json"),
        ):
            raise ReceiptError("Ordered Scenario inputs changed after binding.")
        for held, rebuilt in ((self._before, before), (self._after, after)):
            if len(held) != len(rebuilt) or any(
                original[0] is not current[0]
                or not _same_content(
                    original[2].model_dump(mode="json"),
                    current[2].model_dump(mode="json"),
                )
                for original, current in zip(held, rebuilt)
            ):
                raise ReceiptError("Ordered modifier leaves changed after binding.")
        scenario = self._scenario
        if (
            type(scenario) is not Scenario
            or type(scenario).parts_by_data_load is not self._native_parts
            or ("parts_by_data_load" in vars(scenario))
        ):
            raise ReceiptError(
                "The native Scenario phase adapter changed after binding."
            )
        parts = scenario.parts_by_data_load()
        for phase, part, proof, adapter in zip(
            (True, False), parts, (live.before, live.after), self._adapters
        ):
            expected = bool(proof.parameter_changes or proof.modifier_leaves)
            if not expected:
                if part is not None and (
                    part.parameter_changes
                    or part.simulation_modifier
                    or part.dated_reforms
                ):
                    raise ReceiptError(
                        "An empty ordered phase acquired executable content."
                    )
                continue
            if (
                part is None
                or part.applied_before_data_load is not phase
                or part.dated_reforms
            ):
                raise ReceiptError("The native Scenario timing changed after binding.")
            actual = _parameter_values(part.parameter_changes or {}, encoded=False)
            if (
                not _same_content(actual, proof.parameter_changes)
                or part.simulation_modifier is not adapter
            ):
                raise ReceiptError(
                    "The native Scenario parameters/modifier changed after binding."
                )
            if adapter is not None and (
                type(adapter) is not _OrderedModifier
                or adapter.owner is not self
                or adapter.phase != ("before" if phase else "after")
            ):
                raise ReceiptError(
                    "The ordered execution adapter changed after binding."
                )

    def recheck(self) -> ReformIdentity:
        """Refuse changed plans, original inputs, source/defaults or native phases."""
        self._validate_live()
        return ordered_scenario_reform_identity(self.plan, name=self.name)

    @property
    def identity(self) -> ReformIdentity:
        """An official identity whose receipt-time handle rechecks this execution."""
        identity = self.recheck()
        object.__setattr__(identity, "_recompute_identity", self.recheck)
        return identity

    @property
    def scenario(self) -> Any:
        """The actual native UK Scenario, with checked package-owned adapters."""
        self.recheck()
        return self._scenario

    def __reduce__(self):
        self.recheck()
        before = tuple(
            (function, revision) for function, revision, proof in self._before
        )
        after = tuple((function, revision) for function, revision, proof in self._after)
        return _restore_bound, (
            self.plan.model_dump(mode="json"),
            before,
            after,
            self.name,
        )


def _restore_bound(plan, before, after, name):
    return bind_ordered_scenario_plan(
        plan, before_modifiers=before, after_modifiers=after, name=name
    )


def build_ordered_scenario(
    parameter_changes: Mapping[str, Any] | None = None,
    *,
    before_modifiers: Sequence[tuple[Callable, Mapping[str, str]]] = (),
    after_modifiers: Sequence[tuple[Callable, Mapping[str, str]]] = (),
    name: str | None = None,
) -> BoundOrderedScenario:
    """Build and bind one ordered native Scenario from trusted actual leaves.

    Pass the already-resolved complete common/reference/member parameter map;
    this API applies it once before loading. It never guesses merge/conflict
    policy or extracts leaves from arbitrary native modifier-chain closures.
    """
    from policyengine_uk.utils.scenario import Scenario

    parameters = {} if parameter_changes is None else parameter_changes
    plan, early, late = _make_plan(parameters, before_modifiers, after_modifiers)
    bound = BoundOrderedScenario(plan=plan, name=name)
    bound._parameter_source = parameters
    bound._before_source = before_modifiers
    bound._after_source = after_modifiers
    bound._before = early
    bound._after = late
    before = _OrderedModifier(bound, "before") if early else None
    after = _OrderedModifier(bound, "after") if late else None
    first = Scenario(
        parameter_changes=_native_parameters(plan.before.parameter_changes) or None,
        simulation_modifier=before,
        applied_before_data_load=True,
    )
    second = Scenario(simulation_modifier=after)
    # Native addition supplies its public, reviewed data-load split. The
    # aggregate closure is never inspected or treated as a modifier leaf.
    bound._scenario = first + second
    bound._adapters = (before, after)
    bound._native_parts = Scenario.parts_by_data_load
    bound.recheck()
    return bound


def bind_ordered_scenario_plan(
    plan: OrderedScenarioPlan | Mapping[str, Any],
    *,
    before_modifiers: Sequence[tuple[Callable, Mapping[str, str]]] = (),
    after_modifiers: Sequence[tuple[Callable, Mapping[str, str]]] = (),
    name: str | None = None,
) -> BoundOrderedScenario:
    """Rebind portable plan data to actual trusted job callables; never locators."""
    expected = _validated_plan(plan)
    bound = build_ordered_scenario(
        _native_parameters(expected.before.parameter_changes),
        before_modifiers=before_modifiers,
        after_modifiers=after_modifiers,
        name=name,
    )
    if not _same_content(
        bound.plan.model_dump(mode="json"), expected.model_dump(mode="json")
    ):
        raise ReceiptError(
            "Trusted execution leaves or adapter do not match the ordered plan."
        )
    return bound


_ADAPTER_BINDINGS = {
    name: value for name, value in globals().copy().items() if not name.startswith("__")
}
