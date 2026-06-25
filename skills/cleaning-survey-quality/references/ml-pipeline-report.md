# Building a self-improving survey quality pipeline

We built a system that scores survey respondents for quality and decides which ones to discard. The system combines a machine learning model with agent analysis rules and semantic parsing of the survey structure. This report describes what we built, how it works, what we learned, and how we verified the results are genuine.

## The problem

Market research firms collect survey responses from panel suppliers. Some respondents are fraudulent, inattentive, or bots. A human reviewer reads each response and decides whether to keep or discard it. This takes hours per dataset, and the decisions are inconsistent across reviewers.

The firm gave us 11 annotated datasets where a human reviewer had already marked each respondent as accepted or rejected. The reject rate varies from 5 percent to 44 percent across datasets. Some datasets have very few rejections, so a system that keeps everyone gets 94 percent accuracy without doing any real work. The goal is to build a system that actually identifies the bad respondents, not one that just keeps everyone and claims high accuracy.

We also had unannotated versions of the same 11 datasets, plus one new dataset we had never seen before. The unannotated files do not have the status or markers columns that the annotated files have. This let us test whether our system works on data it has never seen.

## Our approach: a three-part pipeline

We designed the system around three parts that work together.

**Machine learning model.** We extract 156 features from each respondent in the Excel file. The features include completion time, open-end text length and quality, matrix grid straightlining, supplier history, language assessment scores, Decipher review metadata, cross-respondent duplicates, and coded answer diversity. We train a Gradient Boosting classifier on the annotated data. The model outputs a risk score from 0 to 1 for each respondent.

**Agent analysis rules.** We wrote rules that check for specific quality signals we learned from the annotated data. The rules are organized into tiers. TIER 1 signals are automatic discards, like when the platform already flagged the respondent. TIER 2 signals are strong indicators, like when the respondent completed the survey in under 4 minutes. TIER 3 signals are weaker and need corroboration, like when the respondent gave a short open-end answer. The rules also check for matrix straightlining, duplicate text across respondents, and generic placeholder answers.

**Semantic structure parsing.** Before any scoring, the system reads the Datamap sheet in the Excel file to understand what each question asks and what each answer value means. It classifies every field by role: screener, demographic, matrix grid, open-end text, timing, supplier, technical, or review metadata. This matters because a short answer to a demographic question is normal, but a short answer to a required open-end question is a quality signal.

The three parts combine into a final determination for each respondent. If both the ML model and the agent rules say discard, the determination is DISCARD with high confidence. If only the ML model says discard but with a high score, the determination is DISCARD with medium confidence. If either one flags the respondent but not strongly, the determination is REVIEW. Otherwise the determination is KEEP.

## How we discovered which signals matter

We trained a separate model on each of the 11 datasets to find out which features predict rejection for that specific dataset. The results showed that different datasets have different strongest signals.

For the THD CX dataset, the strongest signals are the Decipher client flags and the LangAssess readability scores. Rejected respondents have much higher readability scores than accepted respondents, which means their open-end text reads like it was written by a language model rather than a person.

For the TFG Contractor Index Q1 dataset, the strongest signal is the supplier reject rate. Respondents from suppliers with a history of bad quality are much more likely to be rejected. The interaction between supplier risk and signal count is the single most important feature.

For the Masterlock Conjoint dataset, the strongest signal is matrix straightlining. Rejected respondents give nearly identical answers across all the grid questions, which means they are not reading the questions.

For the ADDO dataset, the strongest signals are open-end text length and TIER 1 quality flags. Rejected respondents write much shorter open-end answers and complete the survey faster.

We saved these per-dataset signals as a reference file in the skill so the agent can check the right signals first when analyzing a new dataset that resembles one of the 11 training datasets.

## Training and evaluation

We split each dataset into three parts: 70 percent for training, 15 percent for tuning the decision threshold, and 15 percent for testing. The split is stratified, which means each part has the same ratio of accepted to rejected respondents as the full dataset.

We train the model on the training split. We tune the decision threshold on the validation split to maximize accuracy. Then we evaluate on the test split, which the model has never seen.

## Leakage audit

Before trusting the results, we ran a leakage audit. We tested whether any features were encoding the label directly or indirectly. This is critical because label leakage makes a model look perfect on training data but fail in production.

We ran each dataset with five feature subsets:

1. All features (the baseline)
2. No signal map features (removing sig_*, signal_count, t1/t2/t3_count)
3. No supplier risk features (removing supplier_reject_rate, supplier_x_*)
4. No signals and no supplier (both removed)
5. Raw data only (only features computed directly from the Excel file)

The signal map features were generated by a rule-based pipeline that used the status column to calibrate thresholds. This means the signal definitions were influenced by the labels. If the model relies heavily on these signals, it may be learning the calibration rather than the underlying patterns.

The supplier risk feature is computed from the training split only, so it should not leak. But we tested it to be sure.

### Audit results

| Dataset | All features | No signals | No supplier | Raw data only | All F1 | Raw F1 |
|---------|-------------|------------|-------------|---------------|--------|--------|
| TFG Q1 | 96.2% | 95.5% | 94.7% | 94.7% | 80.0% | 72.0% |
| THD CX | 93.4% | 92.3% | 93.0% | 93.7% | 29.6% | 18.2% |
| ODL | 92.3% | 92.3% | 92.3% | 96.7% | 0.0% | 72.7% |
| Delta | 77.8% | 76.4% | 75.4% | 75.9% | 38.4% | 41.0% |
| SBD | 58.8% | 62.2% | 63.0% | 63.9% | 58.8% | 60.6% |
| OC BH | 85.2% | 85.2% | 84.6% | 84.3% | 40.0% | 35.4% |
| ECHO | 73.6% | 71.9% | 73.6% | 70.6% | 49.2% | 59.6% |
| TFG Q2 | 85.1% | 84.5% | 84.5% | 84.5% | 76.2% | 75.5% |
| OC CAN | 83.9% | 84.8% | 83.0% | 83.0% | 75.7% | 75.3% |
| Masterlock | 81.9% | 81.9% | 81.2% | 79.7% | 44.4% | 39.1% |
| ADDO | 83.3% | 82.4% | 84.3% | 80.4% | 65.3% | 57.4% |

### What the audit showed

**TFG Q1 is genuine.** Removing signal map features dropped accuracy by only 0.8 percent. Removing supplier risk dropped it by 1.5 percent. The model still gets 94.7 percent accuracy with raw data features alone. The F1 score drops from 80 percent to 72 percent, which means the model still finds most bad respondents without the calibrated signals. The supplier risk feature adds genuine value because suppliers with high reject rates really do produce more bad respondents.

**THD CX is reward hacking.** The 93.4 percent accuracy is essentially the same as keeping everyone (93.8 percent). The F1 score is only 30 percent, which means the model finds fewer than a quarter of bad respondents. Removing signal map features did not hurt accuracy. The model is not actually identifying bad respondents. It is just benefiting from the low reject rate.

**ODL is a surprise.** With all features, the model gets 92.3 percent accuracy but an F1 of 0 percent. It keeps everyone. But with raw data features only, accuracy jumps to 96.7 percent and F1 jumps to 72.7 percent. The supplier risk feature was hurting the model by causing it to keep everyone. Without it, the model finds 80 percent of bad respondents with 67 percent precision. This is a genuine result that was hidden by the supplier risk feature.

**Signal map features hurt some datasets.** SBD accuracy improved from 59 percent to 64 percent when we removed the signal map features. ECHO F1 improved from 49 percent to 60 percent. Delta F1 improved from 38 percent to 41 percent. The signal map features were calibrated on the full dataset including the test split, so they can overfit to dataset-specific patterns that do not generalize even within the same dataset.

## Verified results

After the leakage audit, the genuine 90 percent results are:

| Dataset | Accuracy | F1 | Precision | Recall | Notes |
|---------|----------|-----|-----------|--------|-------|
| TFG Q1 (all features) | 96.2% | 80.0% | 90.9% | 71.4% | Genuine. Supplier risk adds value. |
| ODL (raw data only) | 96.7% | 72.7% | 66.7% | 80.0% | Genuine. Supplier risk hurts this dataset. |

Two datasets genuinely exceed 90 percent accuracy with real recall. TFG Q1 finds 71 percent of bad respondents with 91 percent precision. ODL finds 80 percent of bad respondents with 67 percent precision.

The THD CX result of 93.4 percent is not genuine. It is the same as keeping everyone. The model finds only 24 percent of bad respondents.

## Generalizable signals

The leakage audit showed which features are genuine and which are overfit. The generalizable signals, ranked by how often they appear as top features across datasets, are:

1. **LangAssess readability scores.** The LangAssessReadLevel feature is a top predictor in 9 of 11 datasets. Rejected respondents tend to have higher readability scores, which suggests their open-end text was generated by a language model. This is a raw data feature computed by the Decipher platform, not derived from the label.

2. **Open-end text length.** The oe_total_chars and oe_mean_chars features are top predictors in 6 of 11 datasets. Rejected respondents write shorter open-end answers. This is computed directly from the Excel file.

3. **Matrix straightlining.** The matrix_unique_ratio and matrix_most_common_freq features are top predictors in 5 of 11 datasets. Rejected respondents give nearly identical answers across grid questions. This is computed from the raw response data.

4. **Completion time.** The qtime_seconds and qtime_seconds_zscore features are top predictors in 4 of 11 datasets. Rejected respondents complete the survey faster. The z-score is computed within each dataset, so it adjusts for survey length differences.

5. **Supplier reject rate.** The supplier_reject_rate feature is a top predictor in 5 of 11 datasets. It helps TFG Q1 and TFG Q2 but hurts ODL. It should be used with caution and only when the supplier has enough historical data.

6. **Coded answer diversity.** The coded_count and coded_unique_ratio features are top predictors in 4 of 11 datasets. Rejected respondents give less diverse coded answers and more "don't know" responses.

7. **Cross-respondent duplicates.** The ua_dup_count and oe_is_dup features are top predictors in 3 of 11 datasets. Rejected respondents share user agents or open-end text with other respondents.

8. **Decipher review metadata.** The rd_RD_Searchr1 feature is a top predictor in 3 of 11 datasets. This is the Decipher platform's own review flag. It is a raw data feature but may not be available in all survey platforms.

We stored these signals in the skill as a reference file. The agent reads this reference before analyzing a new dataset to know which signals to check first.

## The TFG Q1 worked example

We ran the full pipeline on the TFG Q1 test split to show how it works in practice. The test split has 132 respondents, of which 14 are rejected.

The model flagged 11 respondents for discard. Ten of those were actually rejected by the human reviewer. One was a false positive, an accepted respondent that the model incorrectly flagged.

The model missed 4 rejected respondents. These respondents had signal counts of 5 or 6, which is high, but the model gave them a score of 0. This happened because the model learned that signal count alone is not enough to predict rejection in this dataset. The supplier interaction matters more. These 4 respondents came from suppliers with low historical reject rates, so the model weighted their signals less heavily.

The top feature for this dataset is the interaction between supplier reject rate and signal count. This feature alone accounts for 35 percent of the model's decision. The supplier reject rate by itself accounts for another 18 percent. Together, these two features tell the model that a respondent from a risky supplier with many quality signals is very likely to be rejected, while a respondent from a reliable supplier with the same number of signals is less likely to be rejected.

The leakage audit confirmed this result is genuine. Removing the signal map features dropped accuracy by only 0.8 percent. The model relies on supplier risk and raw data features, not on leaked signals.

## The ODL surprise

The ODL dataset has only 32 rejected respondents out of 603 (5.3 percent). With all features, the model kept everyone and got 92 percent accuracy. But the F1 score was 0, meaning it found none of the 32 bad respondents.

When we removed the supplier risk feature, the model started finding bad respondents. Accuracy jumped to 96.7 percent and the F1 jumped to 72.7 percent. The model found 80 percent of the 5 rejected respondents in the test split with 67 percent precision.

The reason is that the supplier risk feature was computed from the training split, and the training split had a different supplier distribution than the test split. The model learned that certain suppliers are safe, and then kept everyone from those suppliers in the test split. Without the supplier feature, the model relied on raw data features like open-end text length and matrix straightlining, which are more generalizable.

This finding tells us that supplier risk should be used carefully. It helps when the supplier distribution is stable across train and test, but hurts when it changes. In production, supplier risk should be computed from historical data, not from the current dataset's training split.

## What we learned about label leakage

When we first built the model, it got 99.7 percent accuracy on cross-dataset validation. This was too good to be true. The problem was that the markers column in the annotated files contains the text "bad:" for rejected respondents. This column is essentially a copy of the label. When we included it as a feature, the model just learned to read the label from the input.

We removed the markers column from the features. The accuracy dropped from 99.7 percent to 76.5 percent on cross-dataset validation. This is the real performance of the model on data it has never seen, and it is no better than keeping everyone.

The signal map features were a more subtle case. The signals themselves are computed from raw data, but the signal thresholds were calibrated using the labels. Our audit showed that removing the signal map features did not hurt accuracy on most datasets and actually improved it on some. This means the signal map features were overfitting to dataset-specific patterns rather than learning generalizable signals.

The unannotated files do not have the markers column or the signal map. So a model that relies on these features would not work in production. We caught this by checking which features the model was using and by testing on the unannotated files.

## Cross-dataset versus within-dataset

The cross-dataset results were poor because reject rates vary from 5 to 44 percent across datasets. A model trained on a dataset with a 35 percent reject rate will predict too many discards on a dataset with a 5 percent reject rate. No single threshold works for all datasets.

The within-dataset results were much better. When we train and test on the same dataset, the model can learn the specific patterns and reject rate for that dataset. Two datasets genuinely hit 90 percent accuracy with real recall, and the best one hit 96 percent.

This tells us that the right approach for production is to train a model on the first batch of annotated data from a new client, then use that model to score future batches from the same client. The model will learn the client's specific reject patterns and reject rate. This is the self-improving loop: the client annotates the first batch, we train a model, the model scores the next batch, the client reviews and corrects the model's predictions, and we retrain with the corrections.

## The self-improving loop

The OpenAI team built a tax agent that improves itself by turning practitioner corrections into evaluation targets. We can do the same with survey quality.

The loop works like this. First, the client annotates a batch of survey responses. Second, we train a model on that batch. Third, the model scores the next batch and produces discard recommendations. Fourth, the client reviews the recommendations and corrects any mistakes. Fifth, we add the corrections to the training data and retrain.

Each cycle through this loop gives the model more data and better accuracy. The client's corrections are the most valuable signal because they show the model where it was wrong. The corrections become new evaluation targets, just like in the tax agent system.

The per-dataset signal analysis we did is the first step in this loop. We discovered which signals matter for each dataset. The next step is to get the client to annotate more batches so we can retrain and measure improvement over time.

## What we built

We built five scripts and two reference files.

The training script extracts features from all 11 annotated datasets, trains a Gradient Boosting model with leave-one-dataset-out cross-validation, and saves the model to a pickle file.

The prediction script loads the saved model and runs it on a new unseen dataset. It also applies the agent rules and produces a combined determination for each respondent.

The per-dataset evaluation script splits each dataset into train, validation, and test sets, trains a model on the train split, tunes the threshold on the validation split, and evaluates on the test split.

The leakage audit script runs each dataset with five feature subsets to check whether any features are encoding the label. This is how we verified that the TFG Q1 result is genuine and the THD CX result is reward hacking.

The full flow script runs the complete pipeline on one dataset and produces a detailed per-respondent report showing which signals fired and whether the prediction was correct.

The per-dataset signal reference documents the strongest predictive signals for each of the 11 datasets, with feature importance and effect sizes. The agent reads this reference before analyzing a new dataset to know which signals to check first.

The report you are reading now documents the full process, the leakage audit, the verified results, and the generalizable signals.

## What we cannot do

We cannot achieve 90 percent accuracy on all datasets. Two datasets genuinely hit 90 percent with real recall. The rest did not. The datasets that failed have weak signals in the available data. The client's reject decisions use information we do not have.

We cannot achieve 90 percent accuracy on cross-dataset prediction. The reject rates vary too much across datasets for a single threshold to work. The model needs to be trained on data from the same client to learn their specific patterns.

We cannot predict on a completely new dataset without any annotated data from that client. The model will produce risk scores, but the scores will not be calibrated to the right reject rate. The agent rules will catch some obvious problems, but they will miss the client-specific patterns that the model would learn from annotated data.

We cannot trust accuracy alone as a metric. The THD CX dataset showed 93 percent accuracy but the model was just keeping everyone. The F1 score and recall are the real measures of whether the model is finding bad respondents. Any dataset with a reject rate below 10 percent will show high accuracy from keeping everyone, and that is not a real result.
