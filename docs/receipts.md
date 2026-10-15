# Execution receipts

An execution receipt travels with a published number, such as a dashboard row, a briefing figure or an API response. It names everything that determined that number, so a reader can tell exactly which model, data and certificate produced it, and two numbers can be compared knowing whether they came from the same run.

Schema v1 covers UK results and is defined by `policyengine.provenance.receipt.ExecutionReceipt`. The JSON Schema ships in the wheel at `policyengine/data/schemas/execution_receipt.v1.schema.json`, and the same file is in the repository at [`src/policyengine/data/schemas/execution_receipt.v1.schema.json`](https://github.com/PolicyEngine/policyengine.py/blob/main/src/policyengine/data/schemas/execution_receipt.v1.schema.json).

## What a receipt records

| Field | Contents |
|---|---|
| `wrapper`, `model`, `core` | The `policyengine`, `policyengine-uk` and `policyengine-core` versions that actually ran, read from the installed distributions rather than from the bundle manifest. `install_origin` records a PEP 610 direct URL as `archive`, `directory`, `editable` or `vcs`; it is absent for an ordinary index install with no `direct_url.json`. `wheel_sha256` appears only when the receipt builder verified it. One way is `wheel_paths=` (evidence `installed_record_verified`): the installed files, and any bytecode cache the interpreter would load instead of a source file, are checked against that wheel's RECORD. The other is the installer's recorded archive hash (`installer_archive_hash`), taken only when the install came from a `.whl` URL; a source archive's hash is never recorded as a wheel hash. |
| `data` | The data release and build, and the model version the data was built with (`build_model_version`, distinct from `model.version`). Also the dataset's logical name, URI, revision and the SHA-256 of the bytes that were simulated. The dataset is resolved exactly as `materialize_dataset` resolves it (overlays, per-dataset repository, package and revision, and the release manifest revision when an artifact has none of its own), and the bytes must be the ones the bundle pins for it: a receipt never gives an artifact's name to other bytes. |
| `certification_status`, `certificate` | `certified` only when the bundle certifies all of: the installed model and core versions, that dataset name and those bytes, and the running `policyengine` version. Each package must also have an absent or `archive` install origin, or a `directory` or `vcs` origin with `installed_record_verified` wheel evidence. A directory or VCS install without that evidence produces an `uncertified` receipt, which carries no certificate. An editable install is never certified, whatever the evidence: its wheel holds a pointer to a source tree (a `.pth` file or an import hook) rather than the source, so checking the installed files against it does not bind the code that ran. `certificate_source` records whether the builder read the certificate from the installed bundle (`packaged`) or from a manifest the caller passed (`caller_supplied`). It is the producer's statement, not evidence: trust a certificate only after `verify_certificate` (below). With the packaged bundle, the composition fingerprint of its TRACE TRO is recorded as well. |
| `reform`, `baseline` | Both are required. Each is `current_law` or a digest of the reform bound to its representation (see below). |
| `fiscal_year` | What a year label means: year 2027 is the fiscal year from 6 April 2027 to 5 April 2028, shown as `2027-28`. v1 allows only this convention. |
| `years` | The reported years, sorted and unique. |
| `supported_years` | The years the installed model projects the dataset to, from the dataset's own year (policyengine-uk's `extend_single_year_dataset`, without running a formula; the same rule as the qualification `supported_years` gate). A reported year outside them is unsupported: policyengine-core fills it by carrying or uprating the latest inputs, so its results are not evidence. `unsupported_years` lists them. The certified 1.58.0 dataset projects to 2024–2030, so a 2031-32 figure on it is unsupported. |
| `outputs_sha256` | Optional digest of the output payload the receipt binds. |
| `runtime` | Python version, platform and CI run URL. It is for diagnosis and is part of no digest. |

Malformed `direct_url.json` is refused because the builder cannot determine the package's install origin.

For each loaded top-level package (`policyengine`, `policyengine_uk` and `policyengine_core`), the builder also checks that its `__init__.py` comes from the installed distribution it names. Index, archive, VCS and non-editable directory installs must load the package file listed in that distribution's RECORD, resolved through `locate_file`. Only editable installs (`dir_info.editable: true`) must load from under the directory their PEP 610 URL names, including a `src/` layout. Paths are compared after resolving symlinks. A checkout ahead of a copied install on `PYTHONPATH` is refused because the receipt cannot name the code that ran. An unloaded package has no source path to compare; the version checks still apply.

## Building one

```python
from policyengine.provenance import materialize_dataset
from policyengine.provenance.receipt import build_execution_receipt, reform_identity

source = materialize_dataset("uk")  # the certified release artifact, hash-verified
reform = {"gov.hmrc.income_tax.rates.uk[0].rate": {"2027-04-06": 0.21}}

receipt = build_execution_receipt(
    country_id="uk",
    dataset_path=source.path,
    years=[2027, 2028],
    reform=reform_identity(
        reform, "policyengine.reform_dict/v1", name="basic rate 21p"
    ),
    baseline=reform_identity(None),
    outputs={"budgetary_impact": {"2027": 6.1e9, "2028": 6.4e9}},
)
print(receipt.certification_status, receipt.execution_identity_sha256)
receipt_json = receipt.to_canonical_json()
```

For a country `Microsimulation` built with `managed_microsimulation()`, call `build_execution_receipt_for_microsimulation(sim, years=..., reform=..., baseline=...)`. It reads the dataset that was loaded from `sim.policyengine_bundle`. The file must still hash to the SHA-256 verified when it was loaded, and the receipt must name the dataset, URI, revision and package recorded then; otherwise it is refused, because it would describe bytes that did not run. A simulation loaded from an unmanaged file or URI recorded no load-time hash, so it cannot be receipted. The microsimulation does not record its reform, so pass the reform you built it with.

There are two ways to bind a policyengine-uk `Scenario`:
- A scenario built from `parameter_changes` is bound by content with `scenario_reform_identity(scenario)`.
- `Scenario.from_reform(d)` wraps `d` in a closure that cannot be bound by its code, so bind `d` itself with `reform_identity(d, "policyengine-uk.reform_dict/v1")`.

A scenario with a module-level `simulation_modifier` needs `code_revision={"repository": ..., "git_sha": <full commit sha>}`. The identity then says `binding: "code_revision"` and binds:
- the function's module and qualified name;
- the SHA-256 of its source and of its module's source file;
- the default arguments of every function in that module, encoded with their types and floats by their bits, so `1` and `1.0`, `0.0` and `-0.0`, a tuple and a list, or `None` and a missing key never share a digest (defaults with no exact encoding, such as objects, are refused, and so are two defaults that are one mutable object, such as one list set as both `first` and `second`, since the encoding cannot tell that from two equal lists);
- that revision.

None of these depends on where the code is checked out or which Python version runs it, so CI, a laptop and the server compute the same digest for the same code.

Build the receipt after the run. An identity returned by `scenario_reform_identity` keeps a private handle to the same scenario and code revision. Both receipt builders recompute `reform` and `baseline` identities with handles, and refuse if recomputing is refused or an identity member differs. The handle is excluded from equality, serialization, schemas and digests. A serialized identity loaded back has no handle and is not re-checked; its producer must ensure it describes the run. These checks take snapshots at identity time and receipt build time, so they cannot describe later changes.

**The modifier's module.** A digest can only name what the module's source fixes, so the module holding a bound modifier must have a shape whose state that source determines. At module level it may hold only:
- docstrings and `pass`;
- imports;
- assignments of a literal to one name, annotated or not (`RATE = 0.21`, `YEARS: tuple = (2026, 2027)`);
- undecorated `def` statements, none named like a dunder, whose type parameters (`def pennies[T](amounts: T)`) have no bound, constraints or default;
- an `if __name__ == "__main__":` block with no `else` (it never runs on import, so what it binds is ignored).

Each name is bound once. Defaults hold no `:=`, lambda, comprehension, `await` or `yield`. Annotations allow names, attributes, subscripts, constants, directly signed numeric constants and `X | Y`, with no calls. Anything else is refused, naming the line. That covers:
- a type parameter's bound, constraints or default (`def pennies[T: list[Decimal | float]]`), which Python evaluates only when something such as Pydantic first reads it, so typing's order-insensitive alias cache can decide what it holds;
- conditional, repeated or unpacked bindings;
- objects built at import (`PAYMENT = partial(pay, amount=120)`, whose captured values can change without the source changing);
- values computed from the environment, a file or the clock;
- decorators, class definitions, and code run at import.

The accepted module shape also refuses these constructs:
- arithmetic on literals, such as `WEEKLY = 520 / 52` or `MILLION = 10 ** 6`: use the computed literal (`WEEKLY = 10.0`, `MILLION = 1000000`), or compute the value inside a function;
- `if TYPE_CHECKING:` blocks: put type-only imports in a `.pyi` file or inside a function;
- `type` aliases, such as `type Rate = float`: use the concrete type in annotations, or put the alias in a `.pyi` file;
- starred annotations such as `*args: *Ts`: use a concrete argument annotation or `ParamSpec`'s `P.args` and `P.kwargs`.

Anywhere in the module, code may not:
- tell equal values apart by identity: `is` is allowed only against `None`, `True`, `False`, `...` or `type(...)`, and `type` may not be rebound. The compiler may make equal immutable constants one object, and a digest of values cannot tell one object from two equal ones.
- use `id`, `operator.is_` or `is_not`, `globals`, `vars`, `locals`, `exec`, `eval`, `compile`, `__import__` or `breakpoint`, however imported, or import `builtins`;
- read annotation values through `typing.get_type_hints`, `inspect.signature`, `inspect.getfullargspec`, `get_annotations` or `from_callable`; these explicit metadata readers remain outside the accepted module shape.
- declare a name `global`.
- read dunder attributes other than `__init__` and `__name__`, or dunder names other than `__name__` and `__file__`. Reading a function's or module's own metadata is introspection.
- use `getattr`, `hasattr`, `setattr` or `delattr` with a non-literal attribute name, or a literal dunder other than `__init__` and `__name__`.

Put measure values in literal constants or in default arguments.

**What was imported.** A digest must only name code that ran, so at identity time, and again when a receipt is built with that identity's private handle, the module's source as read now is compiled and checked against what was imported, ignoring file names and line numbers:
- **Versions.** At receipt build time, any recorded version of policyengine, policyengine-uk or policyengine-core must still match its installed version. Independently, each package's distribution metadata must not have been written after this process started. The builder compares the latest modification or change time of its `.dist-info` directory and of the existing `METADATA`, `RECORD`, `INSTALLER` and `direct_url.json` files against `psutil.Process().create_time()`, and refuses metadata written more than two seconds after it. On Linux psutil builds that start time from the boot time in whole seconds plus the start offset in clock ticks, so it can read up to about a second early (one second plus one tick). Without the margin, a process started just after an install finished would be refused. The margin is a blind window: metadata written within two seconds after the reported start is accepted, so an install that lands in that window is not detected. Past it, metadata is refused regardless of import order or whether a version was recorded; an unavailable metadata location is refused too. Restart the process and run again. This also refuses installing a package and then importing it in the same process, such as a notebook `pip install` without a restart, even when that import loaded the new code, unless the install finishes within two seconds of the process starting.
- **Functions.** The source is compiled as a whole, so each function compiles in its module's context, imports included. The modifier and every other function defined in that file must use the module's own globals and match that code, nested code and constants included. Constants are compared by exact type, by IEEE 754 bytes (so a NaN's sign counts) and by how they share objects. Annotation functions that Python 3.14 compiles (`__annotate__`) are the compiler's, not the module's, and a generic function (`def helper[T](...)`, Python 3.12+) is checked through the wrapper the compiler makes to bind its type parameters.
- **Function names.** A `def` name must still be bound to that function, not to another function of the same file or any other object.
- **Code inside functions.** It runs after import, so a type it builds is made then: an expression in a function body, or the annotations, type-parameter bounds and class annotations of a helper defined there (quoted or not). typing caches its generic aliases (`List`, `Dict`, `Optional`, `Annotated`) and user generics (`Generic` subclasses, Pydantic models) by argument equality, and a union equals one holding its members in any order. So `List[Union[Decimal, float]]` built there can return an alias cached for `List[Union[float, Decimal]]`, and Pydantic tries a union's members in order. A function whose code subscripts such a generic with a union or `Literal` is refused. Builtin generics, `collections.abc` classes and classes whose `__class_getitem__` is implemented in C (NumPy's `ndarray` and `dtype`) build a new alias in source order and are allowed (`list[Decimal | float]`), as is a bare `Union[Decimal, float]`. Resolution is conservative. A name stands for every object the module, or any import anywhere inside the function, binds it to, so a helper importing `typing.Sequence` is caught even when a sibling imports `collections.abc.Sequence`. Every string in the function's code that parses as an expression is inspected as a type, since a forward reference such as `Optional['List[Union[Decimal, float]]']` is evaluated when something resolves it. `Literal` values and `Annotated` metadata are left as strings. Local aliases of typing objects (`L = List`) are not followed. The module's own function signatures are compared against their source instead (below).
- **Function metadata.** Each function's name, qualified name and docstring must still be what its `def` made, compared as the compiler stores them. A generic function's `__type_params__` must still be bare type parameters of the names and kinds its source declares, in order, with no bound, constraints, default or declared variance. Each annotation must still hold what its source names, resolved against the module's globals and builtins (and those type parameters): named objects are compared by identity; reconstructed generics, unions and `ParamSpec` argument proxies must have the same origin and arguments, recursively and in order. Source arguments are resolved separately so typing's cache cannot hide a reordered union. Parameterised typing aliases are refused when their source order cannot be checked independently of that cache. Subscripted annotations that do not expose a typing origin and arguments, such as generated Pydantic model classes, are also refused. Quoted annotations and strings stored by `from __future__ import annotations` must match their source, and their resolvable type expressions must also match source order. This includes annotations consumed implicitly by libraries such as `functools.singledispatch`. It must use the builtins module and carry no other attributes (`helper.amount = 240` is state).
- **Defaults.** Literal default arguments in the source, such as `rate=0.21`, must still be the function's defaults, with the same type.
- **Literal constants.** Every literal constant must still hold its value, compared exactly: the same types throughout, floats by their bits, dictionary keys in order, for every literal kind including bytes, sets and complex numbers.
- **No shared mutable objects.** No two literal constants or defaults may be one mutable object, which a value check cannot tell from two equal objects.
- **Imports.** Every imported name must still be what its import binds: `from math import floor` must still be `math.floor`, and `import math` the loaded `math` module. It must hold a module or a callable other than a `functools.partial`; `from __future__` features are the exception. An imported value such as `from params import AMOUNT` is refused even when unused, since code can read a name without naming it. For the same reason, a star import of a module that exports data values is refused; import the callables you use by name. Each name a star import provides must be that module's own.
- **No other names.** The namespace may hold no name the source does not bind, other than the dunders the import system and annotations set. The module's docstring and builtins must be what importing it made. A name set on the module after import is refused however the code would read it.

A measures file edited after import, or a constant, default, import or function reassigned before either snapshot, is refused. If it changes after identity time, a receipt built with the identity's handle refuses the changed modifier, naming the difference or the reason it can no longer be bound. The check does not cover state in other modules (such as `params.PAYMENT` read through `import params`), or data the code reads at run time. Code in other modules is bound by `code_revision` or the installed versions, and `code_revision` names the code, not the process. Receipts are claims by their producer: these checks protect an honest producer against mistakes, not a reader against a producer who builds code to mislead. Code that reaches into frames, the garbage collector or other modules' namespaces is beyond them.

Some modifiers are refused outright because their behaviour depends on values the digest cannot bind: closures, lambdas, nested functions, methods, `functools.partial` and builtins. Anything that is not a `Scenario` is refused too, rather than read as current law.

To check a certificate, call `verify_certificate(receipt, bundle)` with the policyengine manifest for `certificate.bundle_version`. It rebuilds the certificate from that manifest's certification record, the same way the builder does. Then it compares every identity member: the record digest, the basis, the certified model, core and dataset digest, the certifier and the bundle version. It also checks that the receipt's whole `data` identity is the certified dataset with the certified bytes. An empty list means the bundle certifies exactly what the receipt claims, and through the receipt's own rules that pins `model.version`, `core.version` and `wrapper.version` too. `certificate_source`, `qualification_receipt_sha256`, `tro_composition_fingerprint` and wheel hashes are not determined by the bundle, so it does not check them.

Pass the release artifact that was loaded as `dataset_path`. A derived per-year file such as `enhanced_frs_2024_25_year_2026.h5` has different bytes from the artifact the bundle pins, so a receipt for it is refused.

## Digests

Every receipt digest is the lowercase hexadecimal SHA-256 of the [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) canonical JSON of a value, computed in two steps:
1. **Strict JSON conversion.** Only JSON-native values are accepted: strings, booleans, null, integers within ±(2^53−1), finite doubles, arrays and objects with string keys. NumPy boolean, integer and floating scalars are converted to their values, integer keys to their decimal strings, and `datetime.date` to `YYYY-MM-DD`. Anything else is refused rather than silently stringified, including sets, `Decimal`, arrays (0-d and masked ones too, so `np.ma.masked` never becomes `0.0`), NaN and colliding keys.
2. **Null removal.** Object members whose value is `null` are removed. Array elements are kept.

RFC 8785 fixes member order, string escaping and number formatting, so Python and JavaScript produce the same bytes. Removing nulls means a producer that writes `"field": null` and one that omits the field compute the same digest. In Python use `policyengine.provenance.receipt.content_sha256`. In JavaScript:

```javascript
import canonicalize from "canonicalize";
import { createHash } from "node:crypto";

const dropNulls = (v) =>
  Array.isArray(v) ? v.map(dropNulls)
  : v && typeof v === "object"
    ? Object.fromEntries(Object.entries(v).filter(([, x]) => x !== null).map(([k, x]) => [k, dropNulls(x)]))
    : v;
const digest = (value) => createHash("sha256").update(canonicalize(dropNulls(value)), "utf8").digest("hex");
```

Reform digests are the exception: a reform payload is digested with its nulls kept, because there a null can mean something. `Scenario.from_reform({"p": {"2027": None}})` removes a value that `{"p": {}}` keeps, so the two must not share a digest.

The pre-promotion replay interface with policyengine-scorecard follows a different rule, set by its own schemas: plain RFC 8785 over the document as sent, nulls included. `policyengine.provenance.canonical.canonical_sha256` computes that.

| Digest | Value hashed |
|---|---|
| `execution_identity_sha256` | `schema_version`, `country_id`, `wrapper`, `model`, `core`, `data`, `certification_status`, and the certificate's content: bundle version, record digest, basis, certified versions, dataset digest and certifier. Results with the same execution identity recorded the same package identities (versions, install origins and wheel evidence) and the same data under the same certificate, however the receipt was built. For a certified receipt those identities name the code that ran. An uncertified one does not bind its packages' contents: two runs from an editable checkout edited in between share an execution identity. |
| `receipt_sha256` | The whole receipt except `runtime` and the reform and baseline `name` labels. Renaming a measure therefore does not change it. |
| `certificate.certificate_sha256` | The bundle manifest's `data_releases.uk` record. |
| `reform.reform_sha256` | `{"representation": ..., "payload": ...}`, with the payload exactly as given, nulls kept (strict JSON conversion, then RFC 8785, with no null removal). |
| `outputs_sha256` | The output payload. |

Reform digests are never normalized across representations. The same keys can legitimately mean different things in different representations: for example, a bare year in a policyengine-uk country dictionary changes that one year only. So each digest is tied to the representation that was submitted. The v1 representations are `policyengine.parameter_values/v1`, `policyengine.reform_dict/v1`, `policyengine-uk.reform_dict/v1`, `policyengine-uk.scenario/v1` and `policyengine-sim-api.policy/v1`.

## Rules JSON Schema cannot express

Consumers that validate with the JSON Schema rather than the Python model must also check the rules listed under `x-policyengine-rules` in the schema file:

- `years` is sorted with no duplicates, and each year is written as an integer (`2027`, not `2027.0`);
- `supported_years` is sorted with no duplicates, and a year in `years` but not in `supported_years` must be shown as provisional or not at all;
- a certificate is present exactly when the receipt is certified, and it names the receipt's country, model and core versions, dataset digest and `policyengine` version;
- a `current_law` reform has no digest, while any other reform has both a representation and a digest;
- a wheel digest always comes with its evidence;
- a certified receipt has no `editable` package, and no `directory` or `vcs` package without `installed_record_verified` wheel evidence;
- a certificate is trusted only after it, and the receipt's `data`, have been checked against the published manifest it names (`verify_certificate`).

The schema itself fixes the package names (`policyengine`, `policyengine-uk`, `policyengine-core`) and the UK fiscal-year convention, which starts on 6 April.

## Compatibility

Adding an optional field is a compatible v1 change. Optional fields are omitted from digests when absent, so existing digests stay valid. Removing or redefining a field, or changing what a digest covers, requires schema v2.
