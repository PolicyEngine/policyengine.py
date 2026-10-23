# Saturday a133f37a national certification preparation

Branch: `certify-uk-a133f37a-national`, based directly on reviewed #704 head
`da2ae8fb8e97145093e35366686df99c1e38449e`. No #699 prerequisite was applied.
No simulations, national H5 downloads/loads, suites, snapshots or UC-floor
steps ran. Nothing was pushed; no issue or PR was opened.

## Commits and delivery

| Commit | Step |
| --- | --- |
| `d730443d` | PR-body draft and scoped same-line re-cut exception |
| `58e0536c` | Portable #1348 tool, twelve rehearsal patches and application receipts |
| `36d79690` | Guarded 2×2 attribution, source definitions, schema and tiny fixture |
| `bd701bdd` | Sequential runner, exact-cut evidence adapters and pinned metadata |
| Final handoff commit | This handoff, light-check receipt and portable implementation bundle |

The assigned `.git` pointer leads to sandbox-protected caller metadata and was
preserved. Mutable Git metadata and the branch live in **`.job/git`** here:

```bash
GIT_DIR="$PWD/.job/git" GIT_WORK_TREE="$PWD" git log -5 --oneline
GIT_DIR="$PWD/.job/git" GIT_WORK_TREE="$PWD" git status --short
```

Committed `.job/preparation.gitbundle` exports the four implementation commits
through `bd701bdd`, requiring `da2ae8fb`; `git bundle verify` passed. It excludes
its containing handoff commit. This preserves actual #704 branch ancestry even
if Subfleet's salvage ref starts from the original detached checkout. In a new
writable scratch checkout, fetch #704, import the bundle's
`refs/heads/certify-uk-a133f37a-national`, and check out that branch. Do not use a
salvage snapshot without #704 ancestry as the certification base. The previous
committed #704 handoff is preserved in `.job/pr704-HANDOFF.md`.

## Running the separate heavy phase

From this workspace or the imported branch, **after 2026-10-24 00:30Z**:

```bash
export PE_CERTIFY_STORAGE=/private/tmp/uk-a133f37a-national-"$UID"
./run-heavy.sh
```

Storage must be absolute, private, writable and outside every Git repository.
All temporary/cache paths and evidence outputs go there. Supply HF_TOKEN or
HUGGING_FACE_TOKEN; otherwise the runner reads agent-secret in memory. Needs
uv, Python 3.13 access, gh authentication, private HF read access and network.

Before every step: `~/reviews/fleet-ops/tools/reservation.py allowed uk-hub`,
load1 ≤110 and free disk ≥55,000,000,000 bytes (decimal). Tool internal stages
and individual attribution workers also recheck the reservation/resources.
Thread caps and `--test-workers 4` are explicit; evidence steps run serially.

The runner verifies/reconstructs `.job/microcosm`, creates `.job/heavy-repo` on
`preparation-source`, then creates the requested certification branch in
`.job/certification`, descending from the clean preparation commit. The exact
command is in `run-heavy.sh`:

```bash
uv run --no-project --python 3.13 --with huggingface_hub \
  python .job/certify_uk_cut_in_policyengine_py.py \
  --pepy-repo "$PWD/.job/heavy-repo" --base-ref "$PREP_SHA" \
  --branch certify-uk-a133f37a-national --worktree "$PWD/.job/certification" \
  --national-tag microcosm-uk-2024-25-national-20261023T075039Z-a133f37a \
  --drop-regional-release --model-version 2.147.2 --core-version 3.33.3 \
  --test-workers 4 --pr-base budget-local-data-manifest
```

PREP_SHA and tool provenance are resolved by the runner. The tool performs
lock/TROs, snapshots, strict check, UC floor, full suite and generated-file
commit. Other steps verify producer gates, materialize both hash-pinned cuts,
install old model/core, record replay unavailable, run the original #574
contract and Budget-inputs gates with predecessor comparison, run attribution,
and index evidence against the candidate commit/bundle. The uk-data resolver
is unused because it resolves a different producer line. No push/PR flags.

On failure, receipts remain under `$PE_CERTIFY_STORAGE/evidence/`.
`--from STEP` resumes with earlier artifacts and the same preparation/storage.
For an interrupted **uncommitted** tool run: `--from certify --resume-certification`.
For an already committed candidate, resume at replay-status, budget-inputs,
reform-contract, attribution or evidence-index; do not rerun certify over it.
The final index refuses stale receipts and incomplete mechanical stages.

## Runtime planning from the rehearsal

Source `~/reviews/uk-hub/jobs/budget-certify-rehearsal/evidence/timings.csv` is
copied to `.job/rehearsal-timings.csv`. Observations, not guarantees:

| Step | Observed elapsed / planning basis |
| --- | --- |
| Tool/repository preparation | Worktree creation 1–6 s; fresh clone/patching unmeasured |
| Producer gates / old+new materialization | Manifest read 10–15 s; complete artifact download/hash unmeasured, cache dependent |
| Old environment | Installation unmeasured; old-model surface probes 149–233 s were a different operation |
| Initial sync | 2.7–7.0 min |
| certify-data | 22–199 s |
| Lock / certified sync | 4–34 s / 24–138 s |
| Release lock / TROs | 1–5 s / 6–85 s |
| Constants | 1.1–4.3 min |
| Snapshots | 7.2–38.9 min |
| Strict check | 25–49 s |
| UC floor | 5.0–7.7 min |
| Full suite, four workers | 63.7 min: 4,304 passed, 14 skipped, **3 environmental failures**; no passing-duration measurement |
| Replay-unavailable receipt | Unmeasured, metadata only; no replay dispatch |
| Budget-inputs / supported years | No standalone measurement in CSV |
| Full reform contract, seed 0 / max_examples 20 | No standalone measurement; research's 135–145 min estimate covers the older **whole qualification battery**, not this step |
| Four-cell attribution | Unmeasured; budget all four serial national runs |
| Evidence index | Unmeasured, local hashes/metadata |

This national-only route avoids the rehearsal's regional model-surface probes.
Outside-Git TMPDIR addresses the old suite's temporary-directory failures;
that anticipated fix has not been tested here and is not passing evidence.

## Patch provenance and light verification

#1348 source: uk-cut-anyone at `61e25de8a673f4187b2d882acab02d94d4a6da99`.
Direct application initially failed: upstream tool and one test each lacked a
trailing blank line present in the rehearsal source. Separate compatibility
patch restores those two lines. All twelve original files then clean-applied
with git am --no-3way (0007 contains two commits). Separate local adaptation
adds reservation checks, optional branch name and portable provenance. See
`.job/tool-patches/README.md` and `.job/tool-patches.json`. No #699 patch included.

Passed: shell syntax/help, Python AST/help, Ruff on new custom scripts,
source/tree/patch digest verification, and ten attribution light checks for
CLI handling, tiny weighted synthetic schema, missing cross cells and malformed
schema rejection. Receipts: `.job/preparation-checks.json` and
`.job/attribution-light-checks.json`. No repository tests were run.

## Human work still required

- Review real gates/snapshots; obtain fresh explicit acceptance for any UC-floor
  or input gap. #685 does not supply new-cut acceptance. Replay stays
  **unavailable** until the Microcosm replay fix lands, never a pass.
- Review flagged moves against attached model PR/Microcosm histories. The
  mapping file starts empty: path overlap is only a candidate, unmapped moves
  stay **unattributed**. Add named reviewed mappings, then rerun attribution/index.
  Coverage: 84 fiscal/legacy heads, all poverty definitions/HBAI groups,
  FY2026-27–FY2030-31; failed cross cells retain errors and independent effects.
- Confirm old build `810315ac22b81c15c008cfb2723ee99e18725fe4`, inferred from
  the pinned producer certification path. Git verifies it precedes new build
  `829c1bc26c0457c668fe1dfc1e866cb4a752654a`. Reports list missing-variable,
  dependency and disclosure limits. Budget-inputs recomputes the direct
  predecessor; older ever-usable lineage is explicitly not reconstructed.
- Verify/create a certification **issue**, replace first-line
  `Fixes #<certification-issue>` in pr-body.md and add its changelog fragment.
  #574 is a PR, not a suitable issue. Run normal format/lint/PR checks; bind
  evidence again if the candidate changes.
- Heavy-phase job owns pushing/opening the canonical **draft**, stacked on #704.
  Use reviewed pr-body.md plus measured receipts; keep the tool's mechanical
  draft as evidence. This preparation and runner do not push or open PRs.
- Constituency/local-authority outputs remain absent until Monday 26 October,
  unless María (juaristi22) overrides. Dense context (16 absent new inputs,
  0 newly lost variables) is preserved in `.job/dense-schema.json`. Release and
  adoption timing/owners are in pr-body.md; allow for queues, regeneration,
  API deployment and rollback preparation before the Budget go/no-go.
