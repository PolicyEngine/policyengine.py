# Wrapper candidate and publication checks

The nonpublishing `ReleaseCandidate` job produces the stable (`release`) wheel;
`NumericalCandidate` produces the numerical (`rc1`) wheel when an explicit country
artifact is selected. Both use the actual prospective PR merge tree and the
same frozen preparation/build helper as Versioning and Publish. Candidate
artifacts are byte/source evidence; they do not approve numerical results.

This transition must remain on its reviewed PR until the stable Wf artifact,
ordinary CI and the separately agreed numerical/managed checks are complete.
There is no preliminary merge or bypass flag. Before the merge that starts the
unattended Versioning → sentinel → Publish chain, root and the designated peer
must approve the exact head/base, candidate artifact ID/digest, preparation and
toolchain receipts, and the external numerical/managed receipt. The registry/data
publication sequencing remains governed by the separately approved release plan.

## Exact source and intentional holds

- Use a merge commit or squash merge. Rebase merges are unsupported.
- The candidate's recorded PR base must equal the actual current main tip that
  becomes the merge's first parent. If main, the PR head, tags, fragments, source,
  toolchain, runner image or authenticated remote inputs change, create and
  review a new candidate before merging. A rerun of an old event does not refresh
  its historical head/base payload.
- No authenticated stable candidate for that exact head/base is an explicit
  publication hold. Wf preparation itself remains held until its real published
  country/data inputs support the ordinary strict checks. Do not merge while
  this hold is active.
- Tag-state and runner-image equality are deliberate gates. Hosted runner image
  drift requires a reviewed toolchain update and new candidate evidence, not
  a receipt-only exception. The full frozen tool closure and setup-action
  commits are in `.github/release-toolchain.json`.
- Only the current successful Actions attempt is accepted. Artifact creation
  within that attempt's time interval is the producing-attempt discriminator.
  The attempt endpoint describes the same current attempt as the run endpoint,
  not a second independent attestation. A newer
  successful attempt never makes an earlier failed-attempt artifact acceptable.
  Older-attempt artifacts and ambiguous/divergent candidate evidence stop the
  chain. Fixed artifact names can require a fresh PR event/run rather than an
  old-attempt rerun. Preserve failed evidence and obtain review before replacing
  any selected candidate.

The initial source review recorded PR515 head
`1b6c001c860305d529e91d6f452f3359e29439fa` and main base
`6a56ced4f959ce9a1f3b794389a4b42699de8abc`. These identify the preparation change's
starting point only. Subsequent artifact builds and merge approval must record
their own actual current head/base; these historical values authorize no merge.

## Country artifact access and source preparation

The numerical candidate requires a nonempty
`RELEASE_COUNTRY_CANDIDATE_ARTIFACT_ID` naming the actual qualified final-version
country wheel. With no ID, Actions explicitly skips `NumericalCandidate` at job
level. The stable job, Versioning and Publish remain mandatory and never consult
this development input. A supplied invalid, stale or inaccessible ID fails closed;
direct helper invocation without an ID also remains an explicit hold. Clear the
development selection when the numerical qualification window has ended.
The job uses the existing
`APP_ID`/`APP_PRIVATE_KEY` GitHub App with a token restricted to
`PolicyEngine/policyengine-us` and Actions read access; the App installation must
already grant that permission. No token is logged or committed. The stable
candidate ignores this development input and uses ordinary registry evidence.

Wn extras name the selected final country version even before its publication.
Its separate numerical environment therefore installs the authenticated country
wheel out of band with the frozen common dependencies; a plain registry-only
extras install is not the Wn qualification procedure. No local wheel URI enters
the packaged Wn manifest or either TRO. After every generator, identity verification
requires the ordinary US package descriptor and a name/version-only US model
descriptor, and rejects local file URIs in the final manifest and both records.

Generation and immediate prebuild verification run in fresh processes that assert
all imported PolicyEngine modules and package resources originate in the prepared
`src` tree. Both TROs must bind the final manifest bytes. Wn's US record is the
limited manifest-only record; its UK record must exactly match a fresh ordinary
UK reconstruction. The receipt records the manifest and both TRO hashes, and
each corresponding built-wheel member must match. Normal stable generation keeps
its strict data/model checks.

Package and generator inputs must be tracked, including ignored files under
package directories. Untracked source in `src`, `scripts`, `.github` or changelog
inputs fails before preparation/build. Generated Python bytecode and the
backend's `src/policyengine.egg-info` output are excluded from this input check;
they are not candidate policy-source inputs. The sentinel stages tracked updates
and deletions only. It cannot silently add an unauthenticated package input.

## Evidence retained before publication

Candidate jobs retain the actual wheel, source archive and preparation receipt.
Versioning retains its authenticated candidate/tree receipt before creating the
sentinel. Publish retains the byte-comparison receipt and requires the actual
sentinel tree and every wheel member to equal the authenticated stable candidate.
Missing evidence or differing bytes stops before the tag or registry upload.

Bootstrap exports the frozen base dependencies, removes exact-version overlaps
with the validated `.github/release-tools.txt`, and rejects conflicting versions
before installation. That file alone governs overlapping tool hashes. The
toolchain receipt records the actual raw/filtered export hashes, removed pins,
and governing file/hash, freshly derived from the lock for each verification.
Setup, candidate artifact, sentinel and publishing actions are pinned to official
repository commits. Expected API failures report the request path and a bounded
status/access/rate-limit diagnosis without raw stderr, tokens or query strings.

The helper rechecks PyPI absence after rebuilding, immediately before the tag,
and immediately before upload. Only an authoritative version-endpoint 404 counts
as unpublished; a version record with deleted/empty files remains occupied.
Uploads do not skip existing files. A registry race or API failure stops the
release; no success announcement or automatic fallback is authorized by these
checks.
