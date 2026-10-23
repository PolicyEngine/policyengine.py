# Portable certification tool

Upstream is Microcosm #1348, branch `uk-cut-anyone`, commit
`61e25de8a673f4187b2d882acab02d94d4a6da99`. The twelve original rehearsal
patches are copied verbatim and their digests and clean application receipts
are in `../tool-patches.json`. `0007` contains two commits.

The original series did not apply directly to that exact Git commit: its
tool and upstream test each lack one final blank line present in the
rehearsal source snapshots. Apply `0000-tool-trailing-newline-compat.patch`
first. It restores those two blank lines only; the tool's pre-patch blob
then exactly matches `0001`'s expected blob. This file is unrelated to the
rehearsal's `0000-prerequisite-699.patch`, which is deliberately absent.

Apply original `0001` through `0012` in filename order using
`git am --no-3way`. Then apply local
`0013-reservation-branch-provenance.patch` with `git apply --check` and
`git apply --index`, and commit. It adds per-step reservation checks,
optional `--branch`, and portable source provenance. It changes no evidence
requirements or national/regional certification semantics.

Run `python3 .job/prepare-tool.py` to reconstruct these inputs inside the
assigned workspace. It refuses to replace an existing checkout, verifies
the full resulting Git tree and standalone tool SHA-256, and checks the
old/new Microcosm build ancestry. Commit IDs may differ when reconstructing
because the locally applied commits have new committer timestamps; trees
and tool bytes must match. The standalone tool at
`../certify_uk_cut_in_policyengine_py.py` is the exact resulting source.

The heavy runner supplies `PE_CERTIFY_RESERVATION_SCRIPT` and
`PE_CERTIFY_TOOL_SOURCE_COMMIT`. The former invokes
`reservation.py allowed uk-hub` before every timed preflight stage,
subprocess stage, and model-surface calculation. Those stages also enforce
load1 at most 110 and free disk at least 55,000,000,000 bytes. The latter
keeps the Microcosm source identity when invoking the portable snapshot.

Preparation validation was limited to clean patch applications, Git
ancestry, syntax parsing, `--help`, and `git diff --check`. No test suite,
simulation, snapshot, UC-floor command, or national dataset load ran.
