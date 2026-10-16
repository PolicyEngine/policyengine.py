# UK candidate qualification: what the ledger shows, and reproducing a gate

The `certify-uk-release` workflow qualifies each new policyengine-uk wheel
or uk-data release before promotion (`scripts/check_uk_candidate.py`,
`policyengine.provenance.uk_candidate`). Each attempt's gate results and
evidence are written to the `uk-qualification-ledger` branch, which is
public, so the evidence keeps nothing from the survey data that could
identify a record.

## What the ledger withholds

- **Reform contract, population checks.** These run on the survey data. Each
  row's check, route, status and the runner's fixed fields
  (`POPULATION_ROW_FIELDS`) are published; from its `detail`, only top-level
  `True`/`False`/`None` findings are kept, and every count, total, amount,
  text, list or nested mapping reads `"withheld"`. The digest the gate
  records is of that published copy, never of the full report.
- **Metrics review and responsiveness.** The aggregate-impact tool publishes
  a figure from fewer than 10 records as suppressed, and the gate records no
  value from a report that breaks that format; such a report is published
  only as its digest and problems.

## Reproducing a failed population check

The withheld figures exist only in the runner's report, which is not saved.
To see them, rerun the contract on a machine with access to the private UK
dataset, and keep the output local: it holds figures from the survey data,
some from fewer than 10 records, so never commit, paste or publish it.

1. Check out the candidate commit the attempt ran on (`git_commit` in the
   attempt's `harness.json` in the ledger): its bundle manifest names the
   dataset `materialize_dataset` fetches, so an older checkout would fetch
   older data even with the candidate's wheels installed.
2. Install the candidate pair (the attempt's `candidate.json` names the
   wheels) and export `HUGGING_FACE_TOKEN` for the private dataset.
3. Materialize the certified dataset, check its SHA-256 against
   `data.dataset_sha256` in the pair's `pair.json`, and run the contract
   with the seed and sample size in
   `src/policyengine/data/qualification/uk.json`:

   ```python
   import hashlib
   import json
   from pathlib import Path

   from policyengine.provenance.dataset_materialization import materialize_dataset
   from policyengine.tax_benefit_models.uk.budget_reform_contract import (
       run_budget_reform_contract,
   )

   dataset = materialize_dataset("uk", data_dir=Path("data")).path
   pair = json.loads(Path("path/to/ledger/uk/<pair_id>/pair.json").read_text())
   digest = hashlib.sha256(Path(dataset).read_bytes()).hexdigest()
   assert digest == pair["data"]["dataset_sha256"], "not the certified dataset"
   report = run_budget_reform_contract(
       routes=None, dataset_path=str(dataset), seed=0, max_examples=20
   )
   failing = [row for row in report["population"] if row["status"] != "pass"]
   ```

4. Read `failing[...]["detail"]` locally. Report only the finding (which
   condition failed, on which route), never the figures.
