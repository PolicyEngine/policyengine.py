---
title: "Reference"
---

Reference pages are generated from the installed country-model packages. Authored methodology pages explain why the model is structured the way it is; generated reference pages expose the exact release contents.

## What generated reference should include

The variable reference generator already reads the installed country model and can emit:

- one page per variable
- entity, period, unit, value type, and `defined_for`
- variable documentation
- `adds` and `subtracts` relationships
- statutory references where the country model provides them
- source file path and line number
- a program coverage page from `programs.yaml`

## Generate locally

Generate the full US variable reference:

```bash
make docs-generate-reference
```

This writes generated pages under `docs/_generated/reference/us`, which is ignored by Git.

For a fast smoke test:

```bash
make docs-reference-smoke
```

The smoke test generates a CHIP-filtered US reference into `/tmp` and renders it with Quarto. CI runs this target so changes to the generator fail early without checking thousands of generated pages into the repository.

## Next generator layers

The current generator is only the first layer. The same pattern should extend to:

| Layer | Source |
|---|---|
| Parameters | country model parameter YAML |
| Program metadata | `programs.yaml` |
| Data lineage | country data package build metadata |
| Calibration targets | country data package target files and validation artifacts |

Once those layers are generated, authored program pages can stay short and structural, while exact values, citations, source paths, and calibration details remain release-synchronized.
