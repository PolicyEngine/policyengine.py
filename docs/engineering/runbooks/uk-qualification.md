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

1. Install the candidate pair (the attempt's `candidate.json` names the
   wheels) and export `HUGGING_FACE_TOKEN` for the private dataset.
2. Materialize the certified dataset and run the contract with the seed and
   sample size in `src/policyengine/data/qualification/uk.json`:

   ```python
   from pathlib import Path

   from policyengine.provenance.dataset_materialization import materialize_dataset
   from policyengine.tax_benefit_models.uk.budget_reform_contract import (
       run_budget_reform_contract,
   )

   dataset = materialize_dataset("uk", data_dir=Path("data")).path
   report = run_budget_reform_contract(
       routes=None, dataset_path=str(dataset), seed=0, max_examples=20
   )
   failing = [row for row in report["population"] if row["status"] != "pass"]
   ```

3. Read `failing[...]["detail"]` locally. Report only the finding (which
   condition failed, on which route), never the figures.

## A candidate stranded before automatic promotion

Automatic promotion moves main to a qualified candidate only once the newest
run of each workflow and event on the candidate branch, from this repository,
has passed, including a `pr_code_changes.yaml` run dispatched on the branch
itself. Runs of pull requests from other branches or forks at the same
commit do not count. The `refresh-pr-checks` step re-runs a failed, timed-out or
cancelled run until it has had four attempts, within GitHub's 30 days of its
first attempt.

When the candidate waits on a run that refresh will not re-run, the promote
job fails with `::error::<branch> waits on runs refresh will not re-run`,
naming each run, its result and its attempts. That covers a run at four
attempts, one older than 30 days, and one whose result refresh never re-runs
(`action_required`, `skipped`, `stale`, `startup_failure` and the like). The
job fails on every scheduled run until one of these clears it:

- Fix the cause, then re-run the named run by hand
  (`gh run rerun <run id> --repo PolicyEngine/policyengine.py`); a passing
  newest attempt clears it. GitHub refuses this for a run whose first
  attempt is more than 30 days old.
- For the run on the candidate's own tree, dispatch a new one:
  `gh workflow run pr_code_changes.yaml --repo PolicyEngine/policyengine.py --ref <branch>`.
- Requalify the pair: run `certify-uk-release` with its versions, `pair_id`
  and `force` set.

### Another pull request from the candidate branch

A pull request from a candidate branch to a base other than main runs the
same workflows with the same commit and branch as the candidate's own pull
request, and GitHub's run records do not say which pull request a run is
for. While such a pull request is open, or after one was closed or merged
at the candidate's commit, the promote job fails with
`::error::<branch> is not promoted: pull requests ... from it run on the same commit`,
and refresh re-runs none of the candidate's runs. Close that pull request,
then requalify the pair as above: the new candidate commit leaves the other
pull request's runs behind.
