# Client-Process Reconstruction Gaps

[EVOLUTION] — This document is used after client feedback to improve the pipeline. It is not needed for blind runs.

## Context

After running the v4 holistic agent review on ECHO (109-2601, 1566 respondents) and comparing against the client-annotated workbook (260300_ECHO, 553 status=5 discards), we identified 272 false negatives (missed discards) and 203 false positives. This document synthesizes two independent gap analyses:

1. **Signal-lift analysis** — quantifying which raw unannotated fields best explain status=5
2. **Process-gap analysis** — identifying where our review process diverges from the client's cleaning process

The conclusion is that the gaps are **client-process reconstruction gaps**, not "semantic review wasn't smart enough." The client's discard process operates on dimensions we do not currently score.

---

## 1. The Core Problem: Wrong Question

Our framework asks: **"Is this respondent authentic or fraudulent?"**

The client's `badopen` marker asks: **"Does this respondent meet our quality bar for this specific survey?"**

These are fundamentally different questions. On ECHO:

- 553/553 discards have `badopen` in markers
- 553/553 discards have `bad:qualified` in markers
- 553/553 discards have CLASSIFYQuota, TotalQuota, GenderQuota, RegionQuota, ChannelQuota
- 1013/1013 accepted rows start with `qualified,` and have no `badopen`/`bad:` markers

Our fraud signals (TERMFLAGS, AI text, pasted text) catch **12 out of 553 discards (2.2%)** with meaningful lift. The remaining 98% are PM quality judgments that are invisible to our current signal extraction.

---

## 2. Signal-Lift Evidence

### 2.1 Signals With Discrimination Power (Lift > 1.2)

| Signal | Rejected/Total | Reject Rate | Lift | Support | Role |
|--------|---------------|-------------|------|---------|------|
| `qtime_under_4_minutes` | 6/6 | 100.0% | 2.83 | 6 | needs_more_examples |
| `qtime_4_to_5_minutes` | 9/9 | 100.0% | 2.83 | 9 | needs_more_examples |
| `pasted_text_flag` | 2/2 | 100.0% | 2.83 | 2 | needs_more_examples |
| `ai_or_overpolished_text_marker` | 2/2 | 100.0% | 2.83 | 2 | needs_more_examples |
| `termflags_nonzero` | 10/15 | 66.7% | 1.89 | 15 | candidate_rejection_signal |
| `rd_searchr1_8` | 10/16 | 62.5% | 1.77 | 16 | candidate_rejection_signal |
| `rd_searchr1_1` | 10/19 | 52.6% | 1.49 | 19 | context_signal |
| `generic_placeholder_open_end` | 17/35 | 48.6% | 1.38 | 35 | context_signal |

**Problem**: The high-lift signals have tiny support (2-19 rows). They're real but cover <3% of discards.

### 2.2 Signals With NO Discrimination Power (Lift 0.8-1.2)

| Signal | Rejected/Total | Reject Rate | Lift | Support |
|--------|---------------|-------------|------|---------|
| `duplicate_open_end_text` | 529/1490 | 35.5% | 1.00 | 1490 |
| `matrix_near_straightline` | 549/1554 | 35.3% | 1.00 | 1554 |
| `rd_searchr3_united states` | 553/1566 | 35.3% | 1.00 | 1566 |
| `rd_review_nonzero` | 474/1381 | 34.3% | 0.97 | 1381 |

**Problem**: The signals we rely on most (duplicate OE, matrix straightline) have zero discrimination on ECHO. They fire on nearly every row, so they can't separate good from bad.

### 2.3 Protective Signals (Lift < 0.8)

| Signal | Rejected/Total | Reject Rate | Lift | Support |
|--------|---------------|-------------|------|---------|
| `very_short_required_open_end` | 26/127 | 20.5% | 0.58 | 127 |
| `rd_searchr1_5` | 10/40 | 25.0% | 0.71 | 40 |
| `rd_searchr1_6` | 5/22 | 22.7% | 0.64 | 22 |

**Problem**: `very_short_required_open_end` is **protective** — short answers are LESS likely to be discarded. This contradicts our framework's assumption that short OEs are a risk signal. The cross-dataset report confirms this is universal: `very_few_words` (≤3 words) has lift 0.74 across 11 datasets.

### 2.4 Raw-Field Lift (From Captain's Analysis)

These are the strongest raw-field predictors that we are NOT currently using:

| Field | Value | N | Status=5 | Reject Rate |
|-------|-------|---|----------|-------------|
| `CLASSIFY` | 1 (pro) | 250 | 151 | **60.4%** |
| `CLASSIFY` | 2 (consumer) | 1316 | 402 | 30.5% |
| `conditionsAriens` | 1 | 289 | 171 | **59.2%** |
| `conditionsAriens` | 0 | 1277 | 382 | 29.9% |
| `list` | 25 | 548 | 248 | **45.3%** |
| `list` | 139 | 1018 | 305 | 30.0% |
| `PROAGE` | 1 | 197 | 129 | **65.5%** |
| `PROAGE` | None | 1316 | 402 | 30.5% |
| `TERMFLAGS` | 1 | 15 | 10 | 66.7% |
| `TERMFLAGS` | 0 | 1551 | 543 | 35.0% |
| `dcua` | `..` | 739 | 322 | 43.6% |
| `dcua` | `sa` | 570 | 165 | 28.9% |

**Key insight**: CLASSIFY, conditionsAriens, list/source, and PROAGE carry 2x+ discrimination. These are survey-structure fields, not semantic content fields. The client's process is structured around these dimensions.

---

## 3. The Five Process Gaps

### Gap 1: Quota Reconstruction

**What we miss**: The client's discard process is tied to quota cell management. When a respondent is removed from a quota cell (CLASSIFY, CONAGE/PROAGE, REGION, channel, brand-to-rate), the deficit is recorded as a quota marker. We don't reverse-engineer quota cells, so we can't detect quota-incoherent rows.

**Evidence**: Every status=5 row has CLASSIFYQuota, TotalQuota, GenderQuota, RegionQuota, ChannelQuota. CLASSIFY=1 (pro) rejects at 60.4% vs CLASSIFY=2 (consumer) at 30.5%. List 25 rejects at 45.3% vs list 139 at 30.0%.

**What's needed**: Reverse-engineer the client's quota buckets from:
- CLASSIFY (pro vs consumer)
- CONAGE / PROAGE (age brackets per classification)
- REGION (geographic quotas)
- Channel condition fields (conditionsAriens, conditionsHD_or_OPE_dealers, conditionsOther_channel)
- list / source (supplier quotas)
- Brand-to-rate variables (BRANDS2RATEQuota)

Then treat quota-incoherent rows as discard candidates, not just semantic oddities.

### Gap 2: Bad-Open Strictness

**What we miss**: Our framework protects short, on-topic OPE answers because the cross-dataset evidence shows `very_few_words` is a universal non-signal (lift 0.74). But the ECHO client discards them anyway via `badopen`. The client's standard is about **substantive engagement with the survey topic**, not answer length or authenticity.

**Evidence (FN examples from Captain's analysis)**:
- "Mowing and blowing/raking leaves" — authentic, on-topic, but thin → discarded by client
- "Getting my flower garden ready for summer" — authentic but not OPE-specific → discarded
- "I used shovels to dig for garden" — authentic but manual tools, not OPE → discarded
- "Cleaned up fallen branches after a storm using my battery-powered chainsaw and blower" — authentic, on-topic, specific → **still discarded**
- "Purchased a zero term mower to do my yard and make it look better faster" — on-topic but "zero term" (zero-turn) misspelling → discarded

**What's needed**: Field-specific open-end contracts that define what "good" looks like for each OE field in each survey:
- Which fields allow short noun phrases ("Snow Blower", "Home Depot")?
- Which fields require personal project detail with first-person grounding?
- Which "plausible but wrong dimension" answers should fail (e.g., gardening when the survey is about OPE)?
- Per-dataset calibration of the "grounded" requirement (Delta tolerates generic first-person, ECHO does not)

### Gap 3: Brand Funnel / Allocation Logic

**What we miss**: The strongest raw predictors include brand allocation, share, and rating fields — not just open text. We don't check cross-question brand consistency.

**Evidence**: BRANDS2RATEQuota appears 1,040 times across 553 discard rows. The Farnsworth client benchmark showed "Preferred brand inconsistent with consideration/recommendation" as the second-largest flag category (47/1036 respondents). In ECHO, brand-funnel fields (q16, q18, q19_2026, q23_2026_Lr13*, POSSIBLEBRANDSr13) carry more signal than our pass used.

**What's needed**: Relation checks across the brand funnel:
- Awareness → top brands → share allocation → consideration → NPS/ad recall
- Suspicious allocation patterns (e.g., equal share to all brands)
- Brand quota eligibility (does the respondent qualify for the brand cells they were assigned to?)
- Brand name quality in OE fields (correct spellings, real brands vs fake/garbled)

### Gap 4: Consumer vs Pro Branch Handling

**What we miss**: CLASSIFY and PROAGE/CONAGE change the expected answer pattern. A row can sound like a plausible consumer but still fail if it's in the wrong classification branch or provides consumer-style evidence where the quota expects pro-channel behavior.

**Evidence**: CLASSIFY=1 (pro) rejects at 60.4%, PROAGE=1 rejects at 65.5%. conditionsAriens=1 (Ariens dealer channel) rejects at 59.2%. These are all pro-channel indicators with 2x the base reject rate.

**What's needed**: Branch-aware review:
- Pro respondents should show professional purchasing patterns (dealer channels, commercial equipment, volume)
- Consumer respondents should show retail/home-use patterns
- A respondent in CLASSIFY=1 (pro) who answers like a consumer should be flagged
- A respondent in a pro-age bracket (PROAGE=1) who gives consumer-style evidence should be flagged

### Gap 5: Residual Learning from FNs/FPs

**What we miss**: We have 272 FNs and 203 FPs on ECHO alone. These are labeled examples that could be used to learn client-specific discard rules. Currently, we don't do label-aware residual passes.

**Evidence**: The v4 report shows ECHO recall of 0.311 (172 TP, 381 FN). 239 FNs were in the KEEP band — the agent was confident they were good, but the client discarded them.

**What's needed**: A label-aware residual pass that:
1. Reads all 272 FNs and 203 FPs from annotated data
2. Derives a TFG discard rulebook from the patterns
3. Converts FN rows into stricter field-family discard rules
4. Checks against FPs to avoid over-penalizing accepted rows
5. Reruns blind on a fresh pair to validate

---

## 4. Cross-Dataset Heterogeneity

The v4 analysis across 4 datasets confirms that **a single uniform ruleset cannot be optimal**:

| Dataset | N | Client Discards | Agent Discards | Precision | Recall | F1 | Client Tolerance |
|---------|---|-----------------|----------------|-----------|--------|-----|------------------|
| Delta | 1353 | 348 | 613 | 0.333 | 0.586 | 0.425 | Tolerates generic first-person |
| SBD | 787 | 350 | 388 | 0.546 | 0.606 | 0.575 | Middle ground |
| ECHO | 1566 | 553 | 289 | 0.595 | 0.311 | 0.409 | Does NOT tolerate generic |
| ODL | 603 | 32 | 69 | 0.377 | 0.812 | 0.515 | Few discards, fraud only |

**Delta**: Over-discarding (409 FPs). Generic first-person like "I wanted cleaner water" is accepted by client but discarded by agent.

**ECHO**: Under-discarding (381 FNs). Generic first-person like "Mowing and blowing/raking leaves" is discarded by client but kept by agent.

**Root cause**: The "grounded first-person" requirement is too strict for Delta and too lenient for ECHO. The threshold must be calibrated per dataset.

---

## 5. Universal Signals (Generalize Across Datasets)

From the cross-dataset proposition mapping across 11 TFG datasets:

### Strong Universal Signals
- **`meta_praise`** — survey-meta praise ("thank you", "good survey") instead of content. >2x lift in 6/10 datasets. Zero false positives in 5 datasets. **Most reliable OE separator across the TFG portfolio.**
- **`placeholder`** — "None", "N/A", "Nothing", "IDK". >2x lift in 5/6 datasets where it appears.

### Universal Non-Signals (Do NOT Use)
- **`very_few_words`** (≤3 words) — lift 0.74 avg across 11 datasets. Accepted rows are equally likely to give short answers. **Must be down-weighted.**
- **`templated` language** — strong in Delta (47x lift) but not in other datasets. Dataset-specific, not universal.
- **Timing** — rejected rows are faster in 5/11 datasets, slower in 6/11. **NOT a universal driver.**
- **Missing supplier** — only 2/11 datasets show >1.5x lift. Weak and dataset-specific.

---

## 6. What It Would Take to Match the Client's Process

### Phase 1: Obtain Annotated Data (Prerequisite)
- Get `260300_ECHO---client-annotated.xlsx`
- Directly compare badopen vs qualified rows on all visible dimensions
- Reverse-engineer the PM's `badopen` criteria
- Build field-specific open-end contracts per dataset

### Phase 2: Build a Two-Stage Pipeline

**Stage 1 — Universal fraud detection** (what we already do well):
- TERMFLAGS, AI text, gibberish, non-English, pasted text
- High confidence, low coverage (~2% of discards)
- Precision 0.595 on ECHO — when we say discard, we're usually right

**Stage 2 — PM quality assessment** (what we're missing):
- OE substantiveness (depth of engagement with survey topic)
- Brand answer quality (correct names, consistency across questions)
- Answer chain coherence (does the story hang together)
- Off-topic detection (is the OE actually about the survey subject?)
- Classification state (CLASSIFY=1 vs 2 as a scoring prior)
- Survey-specific straightline patterns (per-question battery, not just matrix overall)
- Quota cell coherence (does the respondent fit their assigned quota cells?)

### Phase 3: Per-Dataset Calibration
- Detect client tolerance level from first 100 reviewed respondents, OR
- Use annotated historical data to set thresholds
- Calibrate the "grounded" requirement:
  - Delta: loose (generic first-person is OK)
  - ECHO: strict (require substantive OPE-specific detail)
  - SBD: middle ground
  - ODL: fraud-only (very few quality discards)

### Phase 4: Label-Aware Residual Pass
- After semantic review, apply learned rules from annotated data
- Convert FN rows into stricter field-family discard rules
- Check against FPs to avoid over-penalizing
- Rerun blind on a fresh pair to validate

### Phase 5: Quota/Fielding Reconstruction
- Reverse-engineer quota buckets from CLASSIFY, CONAGE/PROAGE, REGION, channel, list/source, brand-to-rate
- Flag quota-incoherent rows
- Check brand funnel consistency (awareness → share → consideration → NPS)
- Apply consumer vs pro branch logic

---

## 7. ECHO-Specific Recommendations

For ECHO specifically, matching the client's process likely requires a **hybrid approach**:

1. **Semantic review** (current) — catches fraud, AI text, gibberish
2. **Deterministic quota/fielding reconstruction** — catches classification/branch/quota failures
3. **Stricter field-family open-end rules** — catches thin/generic/off-topic OPE answers
4. **Brand funnel consistency checks** — catches brand allocation inconsistencies
5. **Per-dataset calibration** — ECHO requires stricter OE substantiveness than Delta

The expected impact:
- Current: 172 TP, 381 FN, 117 FP (F1 = 0.409)
- Target: ~400 TP, ~150 FN, ~150 FP (F1 = ~0.73)

This requires the annotated workbook to validate. Without it, we're guessing at the PM's criteria.

---

## 8. Current Run Artifacts

The blind ECHO run (109-2601) produced:

| Category | Count | Rate |
|----------|-------|------|
| KEEP | 627 | 40.0% |
| REVIEW | 617 | 39.4% |
| DISCARD | 322 | 20.6% |
| **Total** | **1566** | |

Client ground truth (from 260300_ECHO annotated):
- Status=5 (discard): 553 (35.3%)
- Status=3 (accept): 1013 (64.7%)

Our discard rate (20.6%) is significantly below the client's (35.3%), confirming the under-discarding pattern.

Output files: `autosurvey-outputs/blind-runs-agent/109-2601 Echo BH/holistic_agent_run/`
- `all_judgments.json` — all 1566 judgments with scores + justifications
- `discard_list.json` — 322 respondents flagged for discard
- `review_list.json` — 617 respondents needing human review
- `summary.json` — run metadata
