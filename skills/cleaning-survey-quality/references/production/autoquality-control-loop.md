# AutoQuality control loop

Use this reference when an AutoQuality run is part of an iterative improvement loop.

This adapts the HumanLayer design-control-loop pattern to AutoQuality without the human interview step. The loop is agentic and artifact-driven. The user can still steer it, but the run does not depend on interviewing a human to proceed.

Source pattern: `https://github.com/humanlayer/skills/tree/main/plugins/design-control-loop/skills/design-control-loop`

## Loop components

### Set point

Improve holistic workflow performance across datasets.

Track all of these, not one metric alone:

- strict precision;
- strict recall;
- strict F1;
- soft precision;
- soft recall;
- soft F1;
- false-positive rate;
- false-negative rate;
- validation compliance;
- leakage safety;
- quality of row evidence and exit criteria.

Do not optimize a fixed REVIEW rate or discard rate.

### Sensor

The sensor reads completed run artifacts and reports the gap.

Primary inputs:

- `vN_comparison_results.json`;
- `vN_performance_report.md`;
- `review_compression_report.md`;
- `prior_family_holdout_profile.csv`;
- `normalized/survey_quality.sqlite`;
- `workledger.md`;
- `run_todolist.md`.

Run the local sensor and controller:

```bash
python3 skills/cleaning-survey-quality/scripts/autoquality_control_loop.py \
  --run-dir /path/to/run_dir \
  --output-md /path/to/run_dir/control_loop_report.md \
  --output-json /path/to/run_dir/control_loop_state.json
```

### Controller

The controller chooses one small next loop. It should prefer the smallest change that attacks the largest remaining error bucket.

Use these controller actions:

- `schema_fix`: required fields, validation, or leakage safety failed.
- `fp_guardrail`: strict precision dropped or new false positives appeared.
- `review_compression`: REVIEW is used without named exit questions.
- `auto_keep_holdout`: auto-KEEP false negatives are enriched for a prior family or raw-field pattern.
- `discard_candidate_mining`: strict recall is low and there is hard row-specific evidence that survived accepted-row counterexamples.
- `signal_split`: a broad signal needs to be split into a discriminating child signal.
- `counterexample_update`: a risky signal needs accepted-row guardrails.

Default to `auto_keep_holdout` before `discard_candidate_mining`. A holdout moves rows to REVIEW. It does not create DISCARD.

Once soft false negatives are reduced and strict recall remains low, shift from KEEP-lane holdouts to REVIEW-lane discard candidate mining. Compare REVIEW true positives against REVIEW false positives during evolution, then look for hard row-specific failures that can become DISCARD only after accepted-row counterexamples are documented. Prefer cross-field semantic reconstruction over one-field value rules at this stage.

After a KEEP-lane holdout pass recovers most of a clear text-contract family, do not keep widening the same broad family. Split the remaining false negatives into sharper child signals with evidence and counterexamples. Echo V11 is the reference pattern: invalid q11 other-specify equipment text and hard invalid q17 brand recall were accepted as REVIEW holdouts, while ordinary q17 misspellings stayed context-only because accepted-row counterexamples were common.

For `signal_split`, do not promote opaque coded-value correlations. A child signal must be named in survey terms, tied to field roles or question text, and documented with positive examples plus accepted-row counterexamples. If the normalized Datamap cannot explain the field meaning, the output is a candidate for reconstruction, not a DISCARD rule.

When `signal_split` keeps returning after a large same-dataset gain, prefer validation on another assessed dataset before adding more rules from the same workbook. Continue same-dataset mining only when the next candidate family has clear survey meaning and a separate accepted-row counterexample set.

For cross-dataset transfer, run a coverage check before promotion. The transferred signal must report how many target rows it fires on, positive examples, signal-absent examples, and accepted-row counterexamples when labels exist. If an unlabeled structural probe fires on a broad share of the workbook, keep it as context-only until a sharper child criterion is found. Do not claim accuracy, precision, recall, or F1 from an unlabeled structural probe.

Before implementing a complex controller action, send the proposed loop to Oracle for guidance. Keep the bundle narrow. Include the current control loop report, current and prior performance reports, the candidate plan, and only the scripts or references needed to review the plan. Run Oracle's safety preflight first. Do not send secrets, private data, broad repo globs, raw workbooks, or ambiguous context. Treat the Oracle answer as advisory. Verify it against local artifacts and tests before changing the workflow.

### Actuator

The actuator applies the selected loop.

Allowed actuator outputs:

- updated signal dictionary or signal matrix construction;
- updated no-ML row criteria;
- updated historical priors;
- a new V_next processor or agent prompt;
- a new comparison report;
- SQLite tables for the new version;
- updated `workledger.md` and `run_todolist.md`.

For full row assessment, use Devin CLI print mode with model id `glm-5-2`, one chunk at a time, when agent review is required. Deterministic processors may be used for post-run evolution passes that transform already validated judgments, but they must be labeled as processors, not fresh blind agent runs.

### Dampeners

Every loop must keep these dampeners active:

- no client labels during blind scoring;
- no raw `markers`, `bad:` marker tokens, or status-derived fields during scoring;
- no fixed output-rate targets;
- no promotion from structural transfer without a coverage check;
- every new holdout needs a named exit question;
- every new DISCARD rule needs hard row evidence and accepted-row counterexamples;
- every chunk must pass `validate_agent_judgments.py`;
- every loop must compare against the previous version before it is accepted.

## Standard loop

1. Sense the current state with `autoquality_control_loop.py`.
2. Identify the largest remaining error bucket.
3. Select one controller action.
4. Package the proposed action for Oracle review when the plan is complex. Record the prompt, file scope, response summary, and any adopted guidance in `workledger.md`.
5. Simulate the action on the previous run when possible.
6. Apply the action to create V_next artifacts.
7. Validate every chunk.
8. Merge and compare metrics.
9. Update SQLite, `workledger.md`, and `run_todolist.md`.
10. Promote only durable learnings into the skill.

## Promotion rule

A candidate learning can be promoted into the skill only when it includes:

- the run version where it was found;
- the metric gap it addresses;
- positive examples;
- accepted-row counterexamples;
- how it changes routing;
- why it is not label leakage;
- whether it is a REVIEW holdout or DISCARD evidence.
