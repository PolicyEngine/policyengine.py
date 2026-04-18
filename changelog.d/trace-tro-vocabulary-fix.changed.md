TRACE TRO emission now conforms to the public TROv 2023/05 vocabulary:
switched namespace to `https://w3id.org/trace/2023/05/trov#`, flattened
`trov:hash` nodes to the native `trov:sha256` property, renamed
`trov:path`→`trov:hasLocation` and the inverse pointer on ArtifactLocation
to `trov:hasArtifact`, corrected `TrustedResearchSystem`→`TransparentResearchSystem`
and `TrustedResearchPerformance`→`TransparentResearchPerformance`, and replaced
the locally-invented `ArrangementBinding` chain with
`trov:accessedArrangement` as used by the published trov-demos. Every TRO
now carries `pe:emittedIn` (`"local"` or `"github-actions"`) so a verifier
can distinguish a CI-emitted TRO from a laptop rebuild. Per-simulation TROs
accept a `bundle_tro_url` that is recorded as `pe:bundleTroUrl`, letting a
verifier independently fetch and re-hash the bundle to detect a forged
reference. The composition fingerprint now joins hashes with `\n` to
prevent hex-length concatenation collisions. Adds `policyengine
trace-tro-validate` CLI, removes the broken `--offline` flag, wires
`scripts/generate_trace_tros.py` into the `Versioning` CI job so bundled
TROs ship with every release, inlines the real model wheel sha256 on
`us.json`/`uk.json`, and cleans up the dead `DataReleaseArtifact.https_uri`
/ `_data_release_manifest_url` helpers.
