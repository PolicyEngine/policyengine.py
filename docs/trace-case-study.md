# PolicyEngine as a TRACE case study

_Working draft, April 2026 — prepared after a 2026-04-21 meeting with Lars Vilhuber (AEA Data Editor), Tara Watson (Brookings), John Sabelhaus, Tim Clark, and Casper (TRACE project)._

## What TRACE is for, in the PolicyEngine case

TRACE (Transparent Research And Citation Exchange) defines a standards-based vocabulary — TROv 0.1 at `https://w3id.org/trace/trov/0.1#` — for documenting analytical artifacts by content hash under a SHACL-validatable JSON-LD grammar. A Transparent Research Object (TRO) binds inputs, code, and outputs in a way that a reader who cannot re-run the analysis can still verify that a specific set of files produced a specific set of results.

The question we walked into the meeting with was: where in the PolicyEngine stack does TRACE add real value?

The answer we walked out with is narrower and cleaner than what we had been building toward. TRACE is not a feature of the `policyengine` Python package for researchers running simulations on their own hardware. For that use case, readers who want to check a paper's numbers can just `pip install` the same pins and rerun. TRACE in that loop is documentation, not credibility.

TRACE matters in exactly the places where the reader cannot easily re-run the analysis:

1. **The calibrated microdata build.** Each `enhanced_cps_YYYY.h5` that we publish to Hugging Face is derived from inputs that the public cannot all access directly (IRS-PUF requires agreeing to IRS's terms of use; the build itself takes hours on Modal with specific GPU configurations). Every release emits a TRO that binds the upstream input fingerprints, the build code, and the output h5 under canonical TROv 0.1.

2. **Simulation runs through policyengine.org.** When a researcher uses the webapp to score a reform, we run the simulation on our infrastructure against our pinned calibrated data, and we return the result. A paper that cites that result is asking its readers to trust PolicyEngine's institutional attestation — not to trust that the researcher reproduced a Python pipeline faithfully on their own laptop. A TRO signed by PolicyEngine and served from our infrastructure makes that institutional attestation explicit and machine-verifiable.

## The precise claims a PolicyEngine TRO lets us make

Before TRACE, a paper citing a PolicyEngine result could say: "PolicyEngine-US computed an EITC expansion impact of $X using `policyengine-us==1.653.3` and `policyengine-us-data==1.85.2`." The reader had to take it on faith that those versions, run on that reform, actually produced $X — or install the pins and try it themselves, which presumes the researcher's environment was not modified.

With a TRO emitted by policyengine.org, the paper cites a URL. That URL resolves to a JSON-LD document which the reader can validate with a stock tool. Inside the TRO, pinned by SHA-256:

- The **rules bundle**: wheel hashes for `policyengine` and `policyengine-us` at the version resolved at run time. (We do not pin transitive Python dependencies inside the TRO — TRACE has explicitly not built that in, and a verifier who wants to reconstruct the full environment can resolve the declared dependencies against a public index.)
- The **calibrated microdata**: the `enhanced_cps_2024.h5` SHA-256 and the `DataReleaseManifest` that describes how it was built.
- The **reform**: the full reform JSON submitted by the user, content-hashed.
- The **inputs**: for a household-level simulation, the household JSON the user entered; for an economy-wide simulation, the configuration payload.
- The **outputs**: a content-hashed `results.json` carrying the aggregate metrics the webapp displays, and — for US runs, where the underlying microdata is already public — the full per-household weighted simulation frame as parquet, so downstream researchers can compute custom splits, subgroup analyses, or variables not reported in the paper without re-running the simulation.
- The **institutional attestation**: CI/deploy run URL, git SHA, cloud region, timestamp, and a signature by a PolicyEngine service account.

The claims the TRO supports are, in plain language:

1. _These were the rules, this was the calibrated microdata, and these were the inputs that produced those outputs._
2. _PolicyEngine as an institution ran this simulation; the researcher did not modify the code between our servers and their paper._
3. _Any future reader can recover the full per-household counterfactual frame for re-analysis, bounded only by what we legally can redistribute._

The third claim deserves a design-question flag: whether the webapp TRO binds the full per-household counterfactual frame by default, or only on request, is something we have not settled. There is a real tension — papers cite aggregates; reviewers and follow-up work want distributions, state-level breakdowns, variables the paper did not headline; but a always-default full frame has file-size and privacy-posture costs, especially in restricted-data countries. We intend to make the trade-off deliberately rather than defaulting to either extreme.

One framing point worth being careful about: what PolicyEngine provides is *institution-backed self-attestation*, not arms-length third-party certification. The arms-length property — that the verifier of a claim is structurally independent of the party being audited — is genuinely absent when PolicyEngine both runs the simulation and signs the TRO. What the TRO buys in that case is structured evidence that a reader (or a reviewer) can query, backed by institutional reputation, not cryptographic independence. That is a real step up from "trust me, I ran it" — but we should not market it as more than it is.

## UK data as a strong case for TRACE

In our US work the underlying calibrated h5 is already public on Hugging Face, so a local rerun is in principle possible. That weakens the TRACE value proposition on US — a reader motivated enough to verify could just `pip install` the pins and try it themselves. The TRO still buys institutional attestation (the researcher did not modify the code), but re-running is not materially blocked.

In our UK work the underlying microdata is UK Data Service–licensed and cannot be redistributed. A researcher who wants to verify a UK PolicyEngine result cannot re-run it on their own machine on any reasonable timescale, because they cannot acquire the inputs easily. Institutional attestation is a particularly strong credibility path here, which is why the meeting flagged this kind of scenario as where TRACE adds the most value.

One caveat worth naming explicitly: we are considering publishing a re-calibrated UK variant derived entirely from public-use inputs, which would partially lift the restriction. If that lands, the US and UK cases converge again. And the TRACE project's own plans for external-identifier pinning (UKDS study number + checksum, IRS-PUF agreement number + checksum) — not yet firmed up in TROv at time of writing — would provide an even cleaner mechanism for binding restricted-input provenance without redistribution.

## What is explicitly NOT a TRACE case for us

It is worth being equally clear about where TRACE does *not* add value for PolicyEngine, so we do not accidentally scope it there:

- **A researcher running `policyengine.py` locally and emitting their own TRO.** Readers can `pip install` the same pins and rerun themselves. A TRO is bookkeeping, not a credibility upgrade. The TRO emission helpers in `policyengine.py` exist because they are reused by the two cases above, not because local emission is the flagship user experience.
- **Tracing transitive Python dependencies.** TRACE has, per the meeting, explicitly not built this in, and we should not either. The code documents its declared dependencies; a verifier can resolve them against a public index.
- **Anything that replaces plain version-and-vintage identification.** Much of what matters for reproducibility is just showing "they used that file with that version." That is documentation, not TRACE — and it is often enough on its own, especially for researchers running the Python package against public-use inputs.

## Adjacent workstreams TRACE does not cover

Several reproducibility commitments came up in the meeting that are TRACE-adjacent rather than TRACE-solved. Flagging them so they do not get lost:

- **Preservation-grade archiving.** Hugging Face, where our calibrated h5 artifacts are hosted today, does not publish a preservation commitment comparable to Zenodo or a CLOCKSS / LOCKSS participant. For a TRO citation URL to be durable decades from now, the artifacts it pins need to live somewhere with an explicit long-term preservation policy. Zenodo as a secondary / mirror target is worth serious consideration.
- **PolicyEngine-specific TRACE vocabulary contribution.** We already use `pe:*` extension fields; as we implement and find patterns that generalize (e.g., institution-backed self-attestation, microdata-build provenance, infrastructure-run attestation), contributing those upstream to TROv vocabulary design is in scope.
- **Plain version-identification work outside TRACE.** Version badges, shareable permalinks that resolve to the same numbers, a "why did this number move?" diff view between release pairs. These are separate deliverables that are on our app roadmap; TRACE is not the right frame for them.

Both external-identifier pinning and OS / compute-environment capture are on the TRACE roadmap and would help when they land. We will adopt as they ship.

## What PolicyEngine is building in response

Three concrete workstreams, each tracked as a GitHub issue:

- **`policyengine-us-data`**: each `enhanced_cps_YYYY.h5` release already emits a build TRO. We will verify these TROs are published alongside the h5 and cross-linked from the Hugging Face dataset card so they are discoverable. (us-data PR #746 shipped the emission; issue #808 addresses a parallel licensing-documentation correction.)
- **`policyengine-api`**: emit a TRACE TRO for every webapp simulation run, signed by a PolicyEngine service account, persisted to GCS with durable URL, and exposed on the result response. (Issue #3485.)
- **`policyengine-app`**: surface the TRO as a "Cite this result" action with a citation download panel, an always-visible rules-vs-data version badge so the "rules changed or data changed?" question is answerable at a glance, and shareable permalinks that resolve the same numbers forever. (Issue #2830, blocked on the api work.)

Documentation for researchers is being updated (household-api-docs PR #7) to put the webapp-run citation flow ahead of the local-Python-CLI flow, matching the framing that emerged in the meeting.

## What TRACE gets from us as a case study

A few things we think are worth surfacing to the TRACE project directly:

1. **A use case that is infrastructure-certifying, not author-certifying.** The canonical TRACE scenario is a researcher bundling their code and data. Ours is a web service signing runs on behalf of researchers. The distinction matters for how institutional attestation gets represented in the vocabulary and for what SHACL shapes reject.
2. **Microdata provenance as a first-class artifact class.** Our build pipeline takes hours on specialized hardware and draws on half a dozen upstream sources with varying access levels. The TROv concept of `ArtifactComposition` handles this well, but concrete experience with a working microsimulation build may be useful input as the vocabulary evolves.
3. **A live stress test for `pe:*` extension discipline.** We have a working example of mapping institutionally-specific certification metadata (`pe:certifiedForModelVersion`, `pe:compatibilityBasis`, `pe:emittedIn`, `pe:ciRunUrl`, `pe:ciGitSha`) onto the TRACE core without polluting TROv shapes. If any of those generalize, we would contribute them upstream.

We will keep notes as the implementation proceeds. The TRACE team is welcome to any of this material as part of their grant work.

## Open questions

- **Per-household frame as default or opt-in.** The meeting did not reach consensus on this; we flagged it as unsettled. Default-on has downstream-analysis utility but file-size and privacy-posture costs. Default-off makes TROs smaller but forces downstream researchers to rerun the simulation for any custom split. Design choice should be made deliberately with trade-offs listed, not defaulted to either extreme.
- **Retention and addressing of webapp-run TROs.** These become permanent citations. Commitments needed on durable URLs, content-addressing, migration policy for storage-provider changes, and whether we ever prune. Zenodo as a secondary / mirror target is worth serious consideration — Hugging Face does not publish a preservation commitment, and a TRO URL that 404s in 2040 is a worse outcome than a TRO URL that 404s in a PolicyEngine-controlled bucket.
- **Signing key and key trust model.** A PolicyEngine service-account signature is straightforward to implement; the harder question is how a reader in 2040 verifies the signature belongs to PolicyEngine. Options include a published keychain rooted in a DNS TXT record, a Sigstore-style transparency log, or GCP workload-identity with short-lived signatures. Chain-of-trust design deserves more thought than "we sign it with a service account."
- **Binding to the actual production runtime.** CI run URL + git SHA documents how the container that ran the simulation was *built*. The TRO should additionally bind the running container image SHA, cloud region, and pod / function instance at execution time. Otherwise the TRO only attests to a build, not a run.

Feedback welcomed from Lars, Tim, Casper, Tara, John — and anyone else reading.
