# Engineering Skills

This directory is the canonical source for AI-facing engineering rules.

Tool-specific instruction files such as `AGENTS.md`, `CLAUDE.md`, and
`.github/copilot-instructions.md` should point here instead of duplicating
implementation-specific guidance. When a rule changes, update the skill here
first, then keep adapters thin.

Current skills:

- `github-prs.md`: same-repository PR workflow, required pre-PR checks,
  changelog-fragment requirements, PR head verification, and title conventions.
- `repository-guidance.md`: policyengine.py structure, commands, package
  boundaries, test expectations, and repo-specific anti-patterns.
- `data-certification.md`: certifying country data releases from their
  release manifests, validation semantics, expected files, and legacy paths.
