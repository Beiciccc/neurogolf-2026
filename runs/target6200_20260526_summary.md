# NeuroGolf target 6200 search, 2026-05-26

- Current protected public score: `6101.26`
- Target: `6200.00`
- Required improvement: `+98.74`
- Current best artifact: `runs/iter5108-anazemcev-positive3-over-iter5097/submission.zip`

## Public updates checked

- Latest downloadable public artifacts checked against the current best:
  - `anazemcev/neurogolf-2026-cost-optimal-blend`
  - `seddiktrk/neurogolf-2026-prune-unused-initializers`
  - `koushikkumardinda/neurogolf-championship-the-auto-golfer`
  - `deep262003/baseline-model-2026-neurogolf`
- Result: `0` positive task replacements over the current best.
- The new pruning notebook removes unused initializers from an anazemcev-based bundle, but it provides no positive delta over the current protected best.

## Stability checks

- Added `tools/scan_onnx_stability.py`.
- Current best Conv-bias lint:
  - artifact: `runs/iter5108-anazemcev-positive3-over-iter5097/submission.zip`
  - result: `ok=true`, `conv_bias_issue_task_count=0`
  - output: `runs/stability_lint_iter5108_20260526.json`
- `task315` candidate repeated public-example scan:
  - artifact: `runs/iter5115-task315-rebased-over-iter5108/submission.zip`
  - result: `ok=true`, `repeat=5`, `conv_bias_issue_task_count=0`
  - output: `runs/stability_scan_iter5115_task315_20260526.json`

## Candidate findings

- Historical high-delta rebase over the current best produced only two positive tasks:
  - `task315.onnx`: local `+1.7113`, validation passed, but confidence gate hard-rejected due to blocked/error-prone history.
  - `task251.onnx`: local `+0.0005`, too small to matter.
- The best local-composable candidate is about `6102.97` expected public, far below the `6200` target.
- User-requested manual override submitted `task315` as `manual_task315_rebase_over_iter5108_override`.
- Result: `SubmissionStatus.COMPLETE`, public score `6085.79`; this is a regression from `6101.26`.
- The exact `task315` source sha is now recorded in `runs/public_regression_blocklist.jsonl`.

## Local clean-room trials

The following builders were tested over the current best and did not improve:

- `task110`: local `-2.1425`
- `task061`: local `-4.3398`
- `task245`: local `-15.1820`
- `task168`: local `+0.0000`

## Conclusion

The existing public-artifact and historical-rebase pool is exhausted for a `6200` jump. Reaching `6200` requires new task-level rule models, not recombining current artifacts.

Highest-value next work:

- Build new clean-room rules for low-scoring, unblocked tasks with simple geometry or color logic.
- Continue using full-bundle prediction and stability lint before any submission.
- Avoid historical/error-prone sources even when local public examples pass.
