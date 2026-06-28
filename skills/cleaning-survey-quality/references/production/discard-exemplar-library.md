# Discard Exemplar Library

Calibrated examples of correctly discarded, wrongly discarded, correctly kept, and missed respondents from the Delta Water Filtration v2 annotated run (1,353 respondents, 152 TP, 200 FP, 550 TN, 142 FN-keep, 54 FN-review) and cross-dataset analysis of 4 under-performing datasets (THD CX, Oldcastle Canada, Oldcastle BH, SBD).

Use these exemplars to calibrate discard decisions. Each example includes the signal profile, supplier context, timing, the agent's justification, and the key answer-chain fields that drove the outcome.

---

## 1. True Positives — Correctly Discarded

These respondents were correctly discarded. They represent the patterns where the agent and client agree.

### Pattern A: TIER 1 Signal + High-Risk Supplier (Strongest TP)

**Exemplar: `z6qp8946jmexymtm`**
- Signals: `ai_or_overpolished_text_marker`, `termflags_nonzero`, `duplicate_open_end_text`, `rd_review_nonzero`, `rd_searchr1_22`, `rd_searchr3_united states`
- Supplier: None (high, 40.8% reject rate)
- Timing: 643s (below_median)
- Open-end: "If water has a chlorine taste, odor, or looks slightly cloudy, that's often enough to make someone consider a filter."
- **Why correct**: Two TIER 1 signals (AI marker + termflags). The open-end reads as AI-generated — third-person framing ("often enough to make someone consider"), polished syntax, no personal experience. High-risk supplier amplifies confidence.

**Exemplar: `a1rps7jpejm9049a`**
- Signals: `termflags_nonzero`, `rd_review_nonzero`, `rd_searchr3_united states`, `rd_searchr1_16`
- Supplier: PrimeInsightsGroupLLC-API (moderate, 18.4%)
- Open-end: "**I decided to buy a kitchen sink water filtration device to improve the taste and q..."
- **Why correct**: TIER 1 signal (termflags). Markdown bold formatting (`**`) in an open-end is a strong bot/fraud indicator. Under V7, this should become DISCARD only when the platform signal or model-family convergence meets the calibrated threshold.

### Pattern B: Off-Topic or Nonsensical Open-End

**Exemplar: `0333qv9b7hv27s27`**
- Signals: `matrix_near_straightline`, `rd_searchr1_20`, `ai_or_overpolished_text_marker`, `rd_review_nonzero`
- Supplier: BohemianResearchLLC-API (high)
- Open-end: "This isn't just incompetence — it's fraud masquerading as convenience. Make no mistake: Doorzo is selling you smoke an..."
- **Why correct**: The open-end is completely off-topic (about a company called "Doorzo", not water filtration). TIER 1 signal (AI marker) also present. High-risk supplier.

### Pattern C: Brand-Name-Only or Single-Word Non-Answer

**Exemplar: `rvdq78n6r98r1ffc`**
- Signals: `matrix_near_straightline`, `rd_searchr1_20`, `rd_review_nonzero`, `rd_searchr3_united states`
- Supplier: PrimeInsightsGroupLLC-API (moderate, 18.4%)
- Open-end: "iSpring" (a brand name, not a purchase motivation)
- **Why correct**: The open-end question asks "What prompted you to decide to buy?" and the respondent answered with a brand name, not a reason. This is a non-answer indicating zero engagement with the question.

**Exemplar: `x67jne9s0swkadr7`**
- Open-end: "It's essential"
- **Why correct**: Two-word tautology that doesn't answer the question. However, note this was a **FALSE POSITIVE** in the v2 run — the client kept it. See FP Pattern B below for the distinction.

### Pattern D: Incoherent Demographic Profile + High-Risk Supplier

**Exemplar: `gn7w0ggytpaf5s96`**
- Signals: `rd_searchr1_3`, `rd_review_nonzero`, `rd_searchr3_united states`, `duplicate_open_end_text`
- Supplier: PrimeInsightsGroupLLC-API (moderate, 18.4%)
- Open-end: Claims well water in the District of Columbia (urban, municipal water system)
- **Why correct**: Well water in DC is geographically implausible. The demographic profile contradicts known infrastructure. Combined with moderate-risk supplier and semantic weakness, this is a clear discard.

---

## 2. False Positives — Wrongly Discarded (Client Kept)

These are the most important examples for improving precision. The agent discarded them, but the client accepted them. Study these to avoid over-discarding.

### Pattern A: Short but Legitimate Open-End (MOST COMMON FP)

**Exemplar: `5c2abx3edfkmggta`**
- Signals: `duplicate_open_end_text`, `matrix_near_straightline`, `qtime_5_to_10_minutes`, `rd_review_nonzero`, `rd_searchr1_23`, `rd_searchr3_united states`
- Supplier: PrimeInsightsGroupLLC-API (moderate, 18.4%)
- Timing: 479s (bottom_25)
- Open-end: "better water filter"
- **Why client kept it**: Despite being only 3 words, "better water filter" directly answers the question — the respondent wants a better filter. The client considers this minimally acceptable. The agent was wrong to discard for brevity alone with only TIER 3 signals and a moderate-risk supplier.
- **Lesson**: Short open-ends from moderate-risk suppliers with only TIER 3 signals should NOT be discarded. The client tolerates brief but topically-relevant answers.

**Exemplar: `cpucy5z8vwr1z115`**
- Open-end: "the quality"
- Timing: 267s (bottom_10)
- **Why client kept it**: Despite being only 2 words, the respondent is answering about water quality. Affluent profile ($200K+ HHI) with coherent demographics. Client accepted.
- **Lesson**: Even 2-word open-ends can be legitimate if they are on-topic. Bottom_10 timing alone is NOT a discard signal.

### Pattern B: ALL CAPS but Genuine

**Exemplar: `gjzux42w8qyfe4p6`**
- Open-end: "I WANT THE HIGHEST QUALITY WATER FOR MY BATHS AND I CARE ABOUT MY HEALTH"
- **Why client kept it**: ALL CAPS is unusual but the content is genuine and on-topic. The respondent is expressing a real motivation. Client does not treat ALL CAPS as a discard signal.
- **Lesson**: Formatting quirks (ALL CAPS) alone are NOT discard signals. Focus on content coherence, not formatting.

### Pattern C: Demographic "Incoherence" That Is Actually Plausible

**Exemplar: `pngrtcyptqe4ujk6`**
- Agent discarded because: 5,000-5,999 sq ft home valued under $250K
- **Why client kept it**: Large inexpensive homes exist, especially in rural North Carolina. The open-end ("Because my well water was brown and not clear") is coherent and specific. The client does not treat home-size-to-value ratios as incoherence.
- **Lesson**: Demographic "incoherence" based on home size vs. value is NOT reliable. Rural areas have large inexpensive homes. Do not discard for this alone.

**Exemplar: `38fkz3rhkgzc6y9m`**
- Agent discarded because: 4,000 sq ft condo with $40K-$80K HHI
- **Why client kept it**: The respondent is 25-28 (Gen Z) in Connecticut — could be family-owned or inherited property. Open-end "I need cleaner water" is brief but on-topic.
- **Lesson**: Young respondents with large homes and modest income are not necessarily incoherent. Family wealth, inheritance, or shared living situations explain this.

**Exemplar: `d4x1wx0canyqd2ng`**
- Agent discarded because: Well water in a condominium/townhome
- **Why client kept it**: Some townhome developments do have well water, especially in suburban Pennsylvania. Open-end "I needed an upgrade" is brief but legitimate.
- **Lesson**: Well water in attached housing is uncommon but not impossible. Do not discard for this alone.

### Pattern D: Unemployed with High HHI

**Exemplar: `x556f7ug59gn7y5d`**
- Agent discarded because: Unemployed with $120K-$160K HHI
- **Why client kept it**: Household income includes spouse/partner income. Unemployed respondent with employed spouse is completely normal.
- **Lesson**: Personal unemployment + high household income is NOT incoherent. HHI is household-level, not personal.

### Pattern E: "Don't Know" Answers Are Not Necessarily Fraud

**Exemplar: `3pvzmxucxwhqh3mp`**
- Agent discarded because: "Don't know" for home size, "Not sure" for filtration types
- Open-end: "i'm looking into getting one. t o clean the bad stuff out of the water"
- **Why client kept it**: The open-end is genuine (note the typo "t o" which indicates human typing). "Don't know" / "Not sure" answers indicate uncertainty, not fraud. The respondent is early in their shopping journey ("Just beginning to think about what I want/need").
- **Lesson**: "Don't know" / "Not sure" answers from early-stage shoppers are legitimate. Typos are a positive signal of human authenticity.

---

## 3. True Negatives — Correctly Kept (High Signal Count but Authentic)

These respondents had many client signals (5-7) but were correctly kept because all signals were TIER 3.

### Pattern A: TIER 3 Only + Coherent Open-End = KEEP

**Exemplar: `bvjt4euzygw43bpw`**
- Signals (6): `duplicate_open_end_text`, `matrix_near_straightline`, `qtime_5_to_10_minutes`, `rd_review_nonzero`, `rd_searchr1_20`, `rd_searchr3_united states`
- Supplier: PrimeInsightsGroupLLC-API (moderate, 18.4%)
- Timing: 563s (below_median)
- Open-end: "It felt like my water was a little hard when I get out the shower or bath. My body skin felt dry."
- **Why correct keep**: Despite 6 signals, all are TIER 3 (non-discriminative). The open-end is specific, personal, and sensory ("body skin felt dry"). No TIER 1 or TIER 2 signals. Moderate-risk supplier with coherent profile = KEEP.

### Pattern B: Short but Genuine Open-End + TIER 3 Only = KEEP

**Exemplar: `vewwvywnbcskdyp2`**
- Signals (6): All TIER 3
- Timing: 390s (bottom_10)
- Open-end: "So I could have cleaner water in my house."
- **Why correct keep**: Bottom_10 timing but TIER 3 only. Open-end is brief but directly answers the question. No TIER 1/2 signals = KEEP regardless of timing.

**Exemplar: `fpgfsjpx112qynt5`**
- Signals (6): All TIER 3
- Timing: 272s (bottom_10)
- Open-end: "Cleaner water for sure"
- **Why correct keep**: 3-word open-end, bottom_10 timing, but all TIER 3. The phrase is casual and genuine ("for sure"). No TIER 1/2 = KEEP.

### Pattern C: High Income + TIER 3 Only = KEEP

**Exemplar: `3v996m8qcukgcww0`**
- Signals (6): All TIER 3
- HHI: $200,000+
- Open-end: "the old one got rusted and needs a better change"
- **Why correct keep**: Specific personal experience (rust). All TIER 3. No demographic incoherence. KEEP.

---

## 4. False Negatives — Missed (Agent Kept but Client Rejected)

These respondents were kept by the agent but rejected by the client. They represent the recall gap.

### Pattern A: Over-Polished / Generic Open-End (Client Catches, Agent Misses)

**Exemplar: `n5xkb2r9c3v6ve2q`**
- Signals (6): All TIER 3
- Open-end: "The benefits should be contaminant removal, mineral buildup technologies, multi-stage filtration are considered first before to buy a water filtration device."
- **Why client rejected**: This reads as AI-generated or copied from a product description. It uses technical jargon ("multi-stage filtration", "mineral buildup technologies") and third-person framing ("are considered first"). The client likely flagged this as inauthentic despite no TIER 1 signal.
- **Lesson**: Over-technical, product-description-like open-ends are a missed discard signal. The agent should flag open-ends that sound like marketing copy or product specs.

**Exemplar: `wtyqc8x6xfd0sp5s`**
- Signals (6): All TIER 3
- Open-end: "I wanted cleaner more purified water"
- **Why client rejected**: Generic, could be anyone's answer. The client may have additional context (cross-dataset duplicates, manual review) that the agent doesn't see.
- **Lesson**: Some FNs are indistinguishable from TNs using available signals alone. The client uses information beyond what's in the staged packet.

### Pattern B: Missing Open-End (Agent Missed Blank Response)

**Exemplar: `a12wgw815mwpvmdm`**
- Signals (6): All TIER 3
- Open-end: (not present in first 15 fields — may be blank)
- **Why client rejected**: If the required open-end is blank or missing, the client rejects. The agent kept it because it didn't detect the missing field.
- **Lesson**: Always check if required open-end fields are present and non-empty. Missing required open-ends should be a REVIEW at minimum.

### Pattern C: Indistinguishable from TNs (Recall Ceiling)

**Exemplar: `dq2a49ee6ummf2dz`**
- Signals (6): All TIER 3
- Supplier: PrimeInsights (moderate, 18.4%)
- Open-end: (not shown in first 15 fields)
- **Why client rejected**: Unknown — the answer chain looks identical to TNs. The client may use cross-dataset duplicate detection or manual review.
- **Lesson**: Some FNs cannot be caught with in-packet signals alone. This represents the recall ceiling for signal-based approaches.

---

## 5. Key Decision Boundaries

### Short Open-End Decision Tree

| Open-End Length | Content Type | TIER 1/2 Present | Supplier Risk | Determination |
|----------------|-------------|-----------------|---------------|---------------|
| 1-2 words | On-topic (e.g., "the quality") | No | Moderate/Low | **KEEP** (client tolerates) |
| 1-2 words | On-topic | No | High | **REVIEW** (not auto-discard) |
| 1-2 words | Off-topic / brand name | No | Any | **DISCARD** (Rule 4) |
| 1-2 words | Any | TIER 1 | Any | **DISCARD only if V7 threshold is met** |
| 3-5 words | On-topic, genuine | No | Any | **KEEP** |
| 3-5 words | Tautology ("It's essential") | No | Moderate | **KEEP** (client tolerates) |
| 3-5 words | Tautology | No | High | **REVIEW** |
| Full sentence | Personal, specific | No | Any | **KEEP** |
| Full sentence | AI-like, third-person, polished | No | Any | **REVIEW** (possible FN pattern) |
| Full sentence | Marketing copy / product specs | No | Any | **REVIEW** (client may reject) |
| Any | Any | TIER 1 | Any | **DISCARD only if V7 threshold is met** |

### Demographic "Incoherence" — Do NOT Discard For These Alone

| Pattern | Agent Thought | Reality | Action |
|---------|--------------|---------|--------|
| Large home + low value | "Fabricated data" | Rural areas have large cheap homes | KEEP |
| Well water in condo/townhome | "Geographically implausible" | Some attached housing has wells | KEEP |
| Unemployed + high HHI | "Income incoherence" | HHI is household-level (spouse) | KEEP |
| Young + large home | "Implausible" | Family wealth, inheritance | KEEP |
| "Don't know" home size | "Inattentive" | Legitimate uncertainty | KEEP |

### Timing — Do NOT Use as Discard Signal

| Timing | Action |
|--------|--------|
| bottom_10 | NOT a discard signal. Many TNs have bottom_10 timing. |
| bottom_25 | NOT a discard signal. |
| above_median | Positive signal (slightly predictive of TP when combined with TIER 1) |
| top_10 | NOT a keep signal by itself. Some TPs have top_10 timing. |

---

## 6. Supplier Risk Calibration (Delta-Specific)

| Supplier | Reject Rate | Risk Level | TP Precision | FP Rate | Guidance |
|----------|------------|------------|-------------|---------|----------|
| None (no supplier) | 40.8% | High | 57% | High | Lower discard threshold. TIER 1 is strong evidence. TIER 2 plus semantic weakness can support discard. |
| PrimeInsightsGroupLLC-API | 18.4% | Moderate | 26% | Very High | DO NOT discard for TIER 3 alone. DO NOT discard for demographic "incoherence". Only discard with TIER 1 or clear incoherence (off-topic open-end). |
| Attapoll | ~55% | High | 55% | Low | Standard high-risk treatment. |
| MakeOpinionGmbH-API | ~14% | Low/Moderate | 14% | High | Be very conservative. Most discards are wrong. |
| Qmee | 20.0% | Medium | 17% | High | Be conservative. TIER 1 only for discard. |

**Critical insight**: PrimeInsightsGroupLLC-API accounts for 92 of 200 FPs (46%). The agent is far too aggressive with this supplier. With only 18.4% reject rate and 26% discard precision, the agent should require TIER 1 signals or clear off-topic open-ends to discard PrimeInsights respondents.

---

## 7. Summary Statistics (Delta v2 Run)

| Metric | Value |
|--------|-------|
| Total respondents | 1,353 |
| True Positives (correct discards) | 152 |
| False Positives (wrong discards) | 200 |
| True Negatives (correct keeps) | 550 |
| False Negatives (missed, kept) | 142 |
| False Negatives (missed, reviewed) | 54 |
| **Precision** | **43.2%** |
| **Recall** | **43.7%** |
| **F1** | **43.4%** |
| **Accuracy** | **70.7%** |
| Discard rate | 26.0% |
| Client reject rate | 25.7% |

### Top FP-Producing Patterns (by frequency)

1. **Short open-end + moderate supplier + TIER 3 only** — 68 FPs (34%)
2. **Demographic "incoherence" + moderate supplier + TIER 3 only** — 52 FPs (26%)
3. **ALL CAPS or formatting quirks + moderate supplier** — 18 FPs (9%)
4. **"Don't know" answers + moderate supplier** — 12 FPs (6%)
5. **Bottom_10 timing used as discard signal** — 28 FPs (14%)

### Top TP-Producing Patterns (by frequency)

1. **TIER 1 signal (termflags/AI marker) + high-risk supplier** — 28 TPs (18%)
2. **Off-topic or nonsensical open-end** — 20 TPs (13%)
3. **High-risk supplier + semantic weakness** — 52 TPs (34%)
4. **Brand-name-only or single-word non-answer** — 15 TPs (10%)
5. **Clear demographic impossibility (well water in DC)** — 6 TPs (4%)

---

## 8. Cross-Dataset Calibration Lessons (V2 Full Run)

### Critical Bug: Missing TIER 2 Signals in Staging

The initial V2 staging script filtered out `rd_searchr1_*` and `rd_searchr3_*` signals as "raw search tokens". This was a critical error — `rd_searchr3_canada` and `rd_searchr1_20/22/23` are TIER 2 signals essential for discard decisions.

**Impact on Oldcastle Canada**: 59 of 60 FNs had `rd_searchr3_canada` (TIER 2), but the agent couldn't see it. The agent kept respondents that should have been discarded because it thought there were "No TIER 1/2 signals". After fixing the staging, this signal is now visible and should be used aggressively for Canadian datasets.

**Fix**: The staging script now includes ALL client signals. Never filter out signals without verifying they're not in the TIER classification.

### Critical Bug: Open-End Text Not Read

The answer_chain uses `"text"` as the key for open_text fields (not `"label"` or `"raw_value"`). Subagents that looked for `"label"` found empty strings, leading to incorrect "no open-end" assessments.

**Fix**: Always use `item.get("text")` for items where `answer_type == "open_text"`.

### Dataset-Specific Calibration Issues

#### THD Digital CX (6.2% reject rate — LOW)
- **V2 result**: 0.7% discard rate, 117 FNs, 12 FPs — severely under-discarding
- **Root cause**: All FNs had TIER 3 only signals. Agent kept them per Rule 8.
- **Fix**: For datasets with very low reject rates, the agent needs to use TIER 3 signal combinations more aggressively. 4+ TIER 3 signals + blank/generic open-end + supplier=None should be REVIEW or DISCARD.
- **Key FN pattern**: `duplicate_open_end_text` + `matrix_near_straightline` + `rd_review_nonzero` + `qtime_5_to_10_minutes` + supplier=PrimeInsights(low,8%) → Client rejected, agent kept.

#### Oldcastle Canada (38.4% reject rate — HIGH)
- **V2 result**: 17.6% discard rate, 60 FNs, 71 FPs — significantly under-discarding
- **Root cause**: `rd_searchr3_canada` (TIER 2) was missing from staged data. 59 of 60 FNs had this signal.
- **Fix**: After re-staging with full signals, `rd_searchr3_canada` is visible. Use it as a strong TIER 2 signal: `rd_searchr3_canada` + `qtime_under_4_minutes` + moderate-risk supplier = DISCARD.
- **Key FN pattern**: `rd_searchr3_canada` + `matrix_near_straightline` + `qtime_under_4_minutes` + supplier=PrimeInsights(medium,20.6%) + bottom_10 timing → Client rejected, agent kept.
- **Key FP pattern**: Province "incoherence" (Newfoundland vs Eastern CA) — the agent incorrectly flagged Canadian province/region mappings as incoherent. Do NOT discard for Canadian geographic "incoherence" unless clearly wrong.

#### Oldcastle Brand Health (17.3% reject rate — MODERATE)
- **V2 result**: 20.7% discard rate, 290 FNs, 356 FPs — both high
- **Root cause**: Agent can't distinguish TIER 3 respondents that should be kept vs discarded. Both FNs and FPs have the same signal profile (TIER 3 only).
- **Fix**: Use open-end text quality to distinguish. Read `item.get("text")` for open_text fields:
  - Coherent, specific open-end + TIER 3 only = KEEP
  - Missing/blank open-end + TIER 3 only + moderate-risk = REVIEW
  - Off-topic/incoherent open-end = DISCARD (Rule 4)
- **Key FN pattern**: `duplicate_open_end_text` + `matrix_near_straightline` + `rd_review_nonzero` + supplier=Qmee(low,8.2%) + coherent open-end → Client rejected, agent kept. (Some FNs are indistinguishable from TNs.)

#### SBD Brand Association (44.5% reject rate — HIGH)
- **V2 result**: 77.5% discard rate, 122 FNs, 244 FPs — severely over-discarding
- **Root cause**: Agent discarding high-risk supplier respondents for "semantic weakness" based on short open-ends. The client tolerates brief but on-topic answers.
- **Fix**: DO NOT discard for short open-ends alone, even with high-risk suppliers. Only discard if:
  1. TIER 1 signal present, OR
  2. 2+ TIER 2 signals, OR
  3. Open-end is clearly off-topic/incoherent (not just short)
- **Key FP pattern**: `duplicate_open_end_text` + `rd_review_nonzero` + `rd_searchr1_2` + supplier=PrimeInsights(high,40.6%) + short but on-topic open-end → Client accepted, agent discarded for "semantic weakness".
- **Key FN pattern**: Same signal profile as FP but client rejected. The difference is often in the open-end content quality, which the agent must read and assess.

### Revised Calibration Rules (V3)

1. **Always read open-end text**: Use `item.get("text")` for `open_text` items. Never assume open-ends are empty.
2. **TIER 2 signals are now visible**: `rd_searchr3_canada`, `rd_searchr1_20/22/23` are in the staged data. Use them.
3. **Short open-ends are NOT semantic weakness**: A 3-word on-topic open-end is not a discard signal, even with a high-risk supplier.
4. **TIER 3 signal combinations**: For datasets with low TIER 1/2 rates, 4+ TIER 3 signals + blank open-end + moderate-risk supplier should be REVIEW, not KEEP.
5. **Geographic incoherence**: Do not flag Canadian province/region mappings as incoherent. Do not flag large inexpensive homes in rural areas as incoherent.
6. **Supplier=None**: In some datasets (THD CX, Oldcastle BH), supplier=None has a high effective reject rate. Treat it as high-risk when the dataset's population_stats show it.
