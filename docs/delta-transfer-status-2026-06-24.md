# Delta Transfer Benchmark Status

Date: 2026-06-24

## Current State

The Delta transfer benchmark is in progress and remains label-sealed.

- Blind source: `/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/106-2502 Delta Water Filtration.xlsx`
- Annotated counterpart: `/Users/jeremyalston/Perfect/Annnotated and test'/Data Sets with Cleaning Answer/260111_Delta Water Filtration.xlsx`
- Run directory: `/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/agent-native-delta-transfer-2026-06-24`

The annotated Delta counterpart was not opened by the runner before this status note.

## Completed

- Echo diagnostics were computed from the fixed sealed Echo ledger.
- The provisional client-status threshold was frozen at `0.35` before Delta labels were opened.
- Delta blind context was built for `1,353` respondents.
- The incumbent blind ledger was completed and sealed.
- Incumbent seal hash: `addd62af3954b314487f006875703589c295fe05f033e6b261cbeb864ef4428d`
- The challenger blind run started with the frozen field-first prompt and schema.
- Challenger completed `20` validated batches before the external usage limit stopped further agent worker calls.

## Blocker

`codex exec` now returns:

`ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at 12:59 PM.`

The same limit occurs on `gpt-5.5` and `gpt-5.4-mini`, including a trivial one-line test prompt. This is an external model-invocation limit, not a workbook, schema, reconciliation, or label-access issue.

## Quarantined Feedback

Delta accepted/rejected answer-bank examples supplied during the run were added to the skill as future development evidence with an explicit leakage boundary. They were not fed into the frozen incumbent or challenger prompts for the in-progress Delta transfer test.
