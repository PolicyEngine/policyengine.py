# Agent Instructions

These instructions apply repository-wide.

## Skills System

Canonical AI-facing engineering skills live under `docs/engineering/skills/`.
Use those files as the source of truth across Codex, Claude, Copilot, and other
AI tools.

Before opening, replacing, or sharing any pull request, read
`docs/engineering/skills/github-prs.md`.

Before making or reviewing repository-wide API, testing, documentation, release,
or package-boundary changes, read
`docs/engineering/skills/repository-guidance.md`.

Before certifying or reviewing a country data release, read
`docs/engineering/skills/data-certification.md`.

## Repository Boundaries

`policyengine.py` is the user-facing analysis package. It wraps
`policyengine-uk` and `policyengine-us` with a common `Simulation` object,
dataset loaders, and result models.

Do not bypass the country-model APIs with direct `policyengine-core` calls from
user-facing code unless the change explicitly needs a lower-level primitive.
The wrapper exists so analyses survive country-package and core API changes.

Do not add public input or output classes without Pydantic models. JSON
round-trip is a documented property of the public surface.

Do not cache arbitrary Python objects in public result structures. The
`core.Simulation` output must stay serialisable.
