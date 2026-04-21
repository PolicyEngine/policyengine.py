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

- The **rules bundle**: wheel hashes for `policyengine`, `policyengine-us`, and their transitive Python dependencies at the version resolved at run time.
- The **calibrated microdata**: the `enhanced_cps_2024.h5` SHA-256 and the `DataReleaseManifest` that describes how it was built.
- The **reform**: the full reform JSON submitted by the user, content-hashed.
- The **inputs**: for a household-level simulation, the household JSON the user entered; for an economy-wide simulation, the configuration payload.
- The **outputs**: a content-hashed `results.json` carrying the aggregate metrics the webapp displays, and — for US runs, where the underlying microdata is already public — the full per-household weighted simulation frame as parquet, so downstream researchers can compute custom splits, subgroup analyses, or variables not reported in the paper without re-running the simulation.
- The **institutional attestation**: CI/deploy run URL, git SHA, cloud region, timestamp, and a signature by a PolicyEngine service account.

The claims the TRO supports are, in plain language:

1. _These were the rules, this was the calibrated microdata, and these were the inputs that produced those outputs._
2. _PolicyEngine as an institution ran this simulation; the researcher did not modify the code between our servers and their paper._
3. _Any future reader can recover the full per-household counterfactual frame for re-analysis, bounded only by what we legally can redistribute._

The third claim is the one Sabelhaus surfaced specifically and that we think is underused in microsimulation publishing today. Papers cite aggregate numbers; reviewers and follow-up work want distributions, state-level breakdowns, variables the paper did not headline. A TRO-bound per-household output lets downstream researchers do that custom analysis as re-aggregation rather than re-simulation.

## UK data and the strongest TRACE case we have

In our US work the underlying calibrated h5 is already public on Hugging Face, so a local rerun is in principle possible. That weakens the TRACE value proposition on US — a reader motivated enough to verify could just `pip install` the pins and try it themselves. The TRO still buys institutional attestation (the researcher did not modify the code), but re-running is not materially blocked.

In our UK work the underlying microdata is UK Data Service–licensed and cannot be redistributed. A US researcher who wants to verify a UK PolicyEngine result cannot, even in principle, re-run it on their own machine, because they cannot acquire the inputs on any reasonable timescale. The only credibility path is an institution we trust having run the simulation against data that institution legally controls. That is exactly the central-bank-researcher scenario Lars described in the meeting, and it is the strongest fit for TRACE in the PolicyEngine stack.

Two TRACE features that would make this work cleaner when they land:

- **External-DOI pinning.** Rather than requiring restricted inputs to be redistributable, allow a TRO to pin by external identifier (UKDS study number + checksum, IRS-PUF agreement number + checksum). This lets a validator confirm that the run references the artifact that a qualified researcher could, in principle, acquire.
- **OS and compute-environment capture.** For multi-hour runs on specialized hardware, the Python-package pins do not fully determine reproducibility. Capturing the OS, Python version, and cloud-region provenance in the TRO closes that loop.

Both of these are on the TRACE roadmap per the meeting. We will adopt as they ship.

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

- **Per-household frame as default or opt-in.** We think default-on for countries with public microdata (US) and default-off for countries with restricted microdata (UK). The choice affects TRO file size, privacy posture, and what a reviewer of a UK PolicyEngine paper can actually re-analyze.
- **Retention and addressing of webapp-run TROs.** These become permanent citations. We need to commit to durable URLs, content-addressing, and a policy on how or whether they ever get pruned.
- **Signing key and key rotation.** A PolicyEngine service-account signature is straightforward to implement; the longer-term concern is what happens when we rotate keys or restructure the service. Chain-of-trust design deserves more thought.

Feedback welcomed from Lars, Tim, Casper, Tara, John — and anyone else reading.
