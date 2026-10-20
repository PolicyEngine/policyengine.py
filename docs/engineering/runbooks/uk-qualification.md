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

Any other pull request from a candidate branch runs the same workflows with
the same commit and branch as the candidate's own pull request, and
GitHub's run records say neither which pull request a run is for nor which
base it tested; a pull request's current base does not settle it, since a
base renamed into main records no event. So while another pull request from
the branch is open, or after one was closed or merged at the candidate's
commit (whatever its base), or when the candidate's own pull request's base
was ever changed, the promote job fails with
`::error::<branch> is not promoted: runs at its commit may have tested another base`,
naming the pull requests, and refresh re-runs none of the candidate's runs.
Close those pull requests, then requalify the pair as above: the new
candidate commit leaves their runs behind, and prepare opens a new pull
request to main if none is open.

### What promotion trusts

Promotion guards against mistakes by people who can write to this
repository and against anything people who cannot can do (forks' pull
requests, whatever their branch names, and other pull requests opened from
a candidate branch, which make promotion refuse; one to main that prepare's
lookup adopts is the candidate's own, and promotion refuses it if its base
was ever changed). Whatever else happens, main only
ever becomes the exact qualified commit, built on main as it is at the push,
after the dispatched `pr_code_changes.yaml` run on that commit's own tree
passed. It does not try to resist deliberate disguise by people who can
write here, such as renaming another branch into main to make a run against
another base look like the candidate's: main is not protected, so they
could push it directly. Treat any such change as an incident, not as
something the gate will catch.

## A pair from another data line

Promotion compares only pairs on main's data line (its UK certificate's data
package and repository). While Microcosm UK is the default, the
policyengine-uk-data candidates the workflow resolves are `other_line`: they
are recorded and never promoted, and recovery and check refreshes skip them.

`force` still qualifies such a pair, for evidence. Its candidate commit drops
main's area routing (`--drop-regional-release`), because the routing belongs
to the line the pair would replace, and leaves the test constants that pin
main's certificate as they are, so the candidate's own tests fail. Changing
the data line is a reviewed certification pull request (see
`docs/engineering/skills/data-certification.md`), not a promotion.
