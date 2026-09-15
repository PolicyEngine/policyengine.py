# Canonical SPM wrapper development and remaining release gates

The canonical SPM wrapper integration is **pending promotion**. The packaged
5.3.0 manifest still pins US 1.764.6 and its existing certified Build P release.
Only `measurements.spm` has been staged: forecast content SHA-256
`3d86d5c4c0423480e6b69b75d222ffa4a7a2639e4094df5ba2504af01be17173`, scenario
`ce_trend`, county geography, vintage `2020`. This measurement pin does not
certify the new country package or the enriched data.

The configuration accepts exactly `forecast_content_sha256`, `scenario`,
`geography_kind`, `geography_id`, `county_vintage` and `as_of`. The hash and
scenario are mandatory in a bundle. County and national modes omit
`geography_id`; metro requires it. `as_of`, when present, is an ISO calendar
date. Unknown fields, paths, provider overrides and fallback settings fail
validation. Country runtime validation resolves scenario, year and location
against the pinned artifact when the calculation needs SPM.

## Reproduce the local development fixture

Use a fresh isolated environment containing the exact qualified local country,
calculator and Core wheels. Preserve all earlier qualification environments. Set
`SPM_PYTHON` to that environment's interpreter and `SPM_COUNTRY_WHEEL` and
`SPM_CALCULATOR_WHEEL` to the authenticated wheel paths. The following command
reads wheel `METADATA` and hashes the bytes; it never substitutes an invented
registry release or changes the packaged manifest.

```bash
UV_CACHE_DIR=/tmp/wrapper-spm-uv-cache \
  uv run --python "$SPM_PYTHON" --no-sync python scripts/bundle.py \
  development-manifest \
  --country-wheel "$SPM_COUNTRY_WHEEL" \
  --calculator-wheel "$SPM_CALCULATOR_WHEEL" \
  --output /tmp/wrapper-spm-development-manifest.json
```

The most recently qualified development country wheel is version 1.824.7, SHA-256
`7644819916a4f8ca2aa37a4a9d992fa834bfa66ab2d441326a9686baa5c1a688`.
The observed local calculator wheel is version 1.0.0, SHA-256
`c49c41da5fd482e563eaea956e205a3ba6841cadd4dd32bef4c0c3dbce17ffba`.
These are local development artifacts, not published package identities.
The calculator wheel uses the canonical source commit
`fd7de4b3b670a10acd72567904ccea800252c9a5`. Core remains 3.30.1 and UK 2.90.2.

The fixture records `development.data_certification: not_certified` and
`development.promotion_status: pending`. It removes the inherited US
`certification` and `certified_data_artifact`; inherited data metadata is
reference-only. It records the real local wheel names, versions, file URIs and
SHA-256 hashes. UK release metadata is retained unchanged. It refuses to
overwrite the packaged manifest.

Country model initialization requires a data compatibility receipt even for
household-only tests. An explicitly enabled pytest plugin supplies the
`unverified_development_fixture` receipt and disables remote data-manifest
fetches for that test process. It does not add a compatibility claim, certify a
dataset, or install a production environment-variable override. Its existing
receipt field `certified_for_model_version` names the tested runtime; the
`unverified_development_fixture` basis explicitly denies certification.

```bash
UV_CACHE_DIR=/tmp/wrapper-spm-uv-cache \
  uv run --python "$SPM_PYTHON" --no-sync python -m pytest \
  -p tests.fixtures.spm_development \
  --spm-development-manifest /tmp/wrapper-spm-development-manifest.json \
  tests/test_spm_selection.py tests/test_spm_model.py \
  tests/test_spm_household.py -q
```

The plugin requires explicit opt-in and checks installed US/Core/calculator
versions, both local wheel hashes, and every installed country/calculator
package file against those wheel bytes before country imports. It authenticates
the actual US/Core/calculator import origins and package search paths, rejects
shadowing from `PYTHONPATH` or previously loaded modules, and repeats these
checks after bootstrap. Core wheel bytes are checked by the separate four-wheel
native probe. Only focused household
and synthetic small-dataset tests belong in this command. The final acceptance
worker owns the heavy population process. Local enriched H5 experiments require
an explicit path with `allow_unmanaged=True` and remain development runs while
certification is pending.

An explicitly labeled development script can use the same bootstrap before
importing country models. This helper lives under `tests/fixtures` and is not a
production environment override:

```python
from tests.fixtures.spm_development import activate_spm_development_manifest

development = activate_spm_development_manifest(
    "/tmp/wrapper-spm-development-manifest.json"
)
import policyengine as pe

assert development["development"]["promotion_status"] == "pending"
assert pe.us.model.data_certification.compatibility_basis == (
    "unverified_development_fixture"
)
```

Run such a script from the wrapper worktree with the isolated interpreter and
`uv run --python "$SPM_PYTHON" --no-sync`. The final acceptance worker can
then call `pe.us.managed_microsimulation(dataset=LOCAL_H5,
allow_unmanaged=True, spm={...})`, reporting the explicit development receipt.
Only that worker is authorized for the heavy population process.

Bundle-only tests avoid the country bootstrap entirely:

```bash
UV_CACHE_DIR=/tmp/wrapper-spm-uv-cache POLICYENGINE_SKIP_COUNTRY_IMPORTS=1 \
  uv run --python "$SPM_PYTHON" --no-sync python -m pytest --noconftest \
  tests/test_spm_bundle_tooling.py tests/test_bundle_metadata.py \
  tests/test_bundle.py -q
```

## Stage and later verify published measurement pins

The operator command validates all settings before writing. Omitting
`--calculator-version` stages only configuration and preserves package pins
and data certification:

```bash
uv run --python "$SPM_PYTHON" --no-sync python scripts/bundle.py set-spm \
  --forecast-content-sha256 3d86d5c4c0423480e6b69b75d222ffa4a7a2639e4094df5ba2504af01be17173 \
  --scenario ce_trend
uv run --python "$SPM_PYTHON" --no-sync python scripts/bundle.py check
```

After the calculator's actual registry release is authorized and published,
repeat `set-spm` with `--calculator-version "$PUBLISHED_CALCULATOR_VERSION"`.
The command fetches that exact version's authoritative PyPI metadata, requires
one non-yanked universal wheel on `files.pythonhosted.org`, downloads its bytes,
and checks the registry SHA-256 before writing. It adds `spm-calculator` as a
hashed `runtime_dependency` scoped to the US, adds it to US/models/dev extras,
and preserves UK requirements. The version must come from the real release;
local wheel metadata is not proof of registry publication.

`scripts/bundle.py check --published-spm` checks the measurement pin and
published calculator dependency metadata. **It does not establish country/data
compatibility or whole-release readiness.** It rejects development fixtures and
currently exits 2 with `SPM promotion pending: no published spm-calculator pin`.
Ordinary `check` passes for the staged draft; this is metadata consistency only.

## Exact work remaining before a production bundle

1. Complete the coordinator's canonical numerical acceptance and source/review
   gates. Deploy the separately owned protections for old bundle images before
   calculator publication. Record the reviewed source and actual published
   calculator wheel identity and import/content verification.
2. Authenticate the producer's clean reviewed source and build a new immutable
   native source-enrichment release. The completed producer handoff records a
   local candidate at `/private/tmp/microcosm-spm-native-role-final-20260909`,
   whose H5 SHA-256 is
   `6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84`.
   The candidate is not published or certified. The new person primitive is
   `is_spm_independent_minor_role`; all prior fields, values, dtypes, membership,
   county inputs and weights are preserved. This is source enrichment, not
   recalibration. The inherited diagnostics remain schema 5, SHA-256
   `870449b44e86b13b25bcea1a57f0e7af37f4d4db18be815eea3acdf9fe6eb40e`;
   relabeling those diagnostics as schema 6 is invalid.
3. In the producer checkout, run its real `python -m
   microcosm.data.source_enrichment --certify` contract with the new candidate,
   exact parent H5 and actual country/Core/wrapper compatibility wheels. That
   contract verifies native loaders, registration, input precedence and wheel
   source identities without a full population simulation. Run the actual
   publisher's `--preflight-only` contract. The producer handoff contains the
   full commands. Commit authentication and compatibility evidence are still
   required; no edited compatibility ranges can replace them.
4. Publish the reviewed immutable enrichment release only after its real gates
   pass. Resolve the actual country/wrapper publication sequence with the
   coordinator; do not invent future versions to break that dependency.
   Refresh country and wrapper locks against real registry bytes.
5. Certify the published data release through `scripts/bundle.py certify-data
   --country us --data-producer populace --model-version
   "$PUBLISHED_COUNTRY_VERSION" --manifest-uri "$PUBLISHED_RELEASE_MANIFEST_URI"`.
   The URI must identify the actual immutable producer release. This command
   updates the country pin and data metadata from real compatibility evidence.
   Regenerate bundle artifacts and TRACE sidecars, inspect full-manifest hash
   bindings, and run the required exact model/data tests. Staging an SPM hash
   changes the manifest bytes; old sidecar bindings cannot establish provenance
   for those new bytes.
6. Finish the coordinator-owned final population, simulation beta, API staging,
   browser/client and production version-route acceptance. The focused local
   tests above do not establish those deployment gates.

No release, publication, deployment, full population run or data certification
was performed by this wrapper tooling work.

The bundled TRACE sidecars are regenerated against the current manifest, so
`TestVendoredSidecarBinding` passes: both `us.trace.tro.jsonld` and
`uk.trace.tro.jsonld` bind manifest SHA-256
`d430b8e561d76e5836a17bf506b06b9cd16560eb77f15718dd46f4e78513de85`, which is
the hash of `src/policyengine/data/bundle/manifest.json` in this tree. That
binding covers the staged measurement bytes only; it is metadata provenance,
not data certification, and the sidecars must be regenerated and reviewed again
at the real bundle promotion step against published artifacts.
