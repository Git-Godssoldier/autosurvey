# Dataset Normalization And SQLite Store

Use this reference when a run needs durable, queryable survey data before scoring, benchmarking, error analysis, or reporting.

## Purpose

Normalize each Decipher workbook into a SQLite database so every later step can be audited with SQL. The database is an analysis substrate, not a replacement for the original workbook.

## Required Store

Create the SQLite database under the run output directory:

`{output_dir}/normalized/survey_quality.sqlite`

Also write:

- `{output_dir}/normalized/schema_summary.md`
- `{output_dir}/normalized/field_roles.csv`
- `{output_dir}/normalized/import_report.json`
- `{output_dir}/normalized/analysis_queries.sql`

## Procedure

1. Verify inputs.
   - Confirm the workbook exists and has a respondent sheet plus `Datamap` when available.
   - If the run depends on an external database or MCP source, verify access first. If unavailable, stop and tell the user which connection is missing.

2. Map field roles before scoring.
   - Classify fields as identifiers, status/client labels, review markers, screeners, quotas, brand funnel, equipment ownership/use, matrix cells, narrative open ends, other-specify fields, timing, supplier/source, technical/device fields, and unknown.
   - Use Datamap question text and value labels where available. Do not infer role from a column name alone when Datamap evidence exists.

3. Normalize into SQLite.
   - Keep raw workbook values lossless in `responses_wide`.
   - Store one row per respondent in `respondents`.
   - Store one row per field in `fields`.
   - Store one row per respondent-field answer in `answers_long`.
   - Store Datamap metadata in `datamap_entries`.
   - Store generated features in `features`.
   - Store agent judgments in `agent_judgments` when available.
   - Store client labels and markers in `client_labels` when available.
   - Store evaluation rows in `evaluation_results` when comparing to ground truth.

4. Preserve raw-to-normalized traceability.
   - Every normalized answer must carry `respondent_id`, original row number, field name, raw value, normalized value, field role, and source workbook path.
   - Never overwrite the source workbook.

5. Query incrementally.
   - Start exploratory SQL with `LIMIT`.
   - Use CTEs for readable metrics.
   - Handle nulls explicitly.
   - Save final SQL in `analysis_queries.sql`.

6. Sanity check the store.
   - Respondent count equals workbook data rows.
   - `answers_long` count equals respondent count times imported field count, unless blank-only fields were intentionally excluded and recorded in `import_report.json`.
   - UUID/record uniqueness is reported.
   - Status distribution, marker distribution, supplier counts, timing min/max, and open-end blank rates are included in `schema_summary.md`.

7. Use SQLite for analysis.
   - Compute accuracy, precision, recall, F1, specificity, balanced accuracy, soft recall, and review volume with SQL when evaluation labels exist.
   - Query FP/FN cohorts by ML band, convergence count, evidence families, OE class, field role, branch, quota, brand funnel, timing, supplier, and technical fields.
   - Save query outputs to CSV or JSON when they drive a report.

8. Report data issues.
   - Flag missing Datamap, duplicate respondent IDs, impossible status values, blank required fields, extreme timing values, unexpected label imbalance, and columns that could not be role-mapped.

## Minimal Schema

```sql
CREATE TABLE respondents (
  respondent_id TEXT PRIMARY KEY,
  record TEXT,
  source_row INTEGER NOT NULL,
  source_workbook TEXT NOT NULL
);

CREATE TABLE fields (
  field_name TEXT PRIMARY KEY,
  field_role TEXT NOT NULL,
  question_text TEXT,
  value_labels_json TEXT,
  source TEXT NOT NULL
);

CREATE TABLE answers_long (
  respondent_id TEXT NOT NULL,
  field_name TEXT NOT NULL,
  source_row INTEGER NOT NULL,
  raw_value TEXT,
  normalized_value TEXT,
  field_role TEXT NOT NULL,
  PRIMARY KEY (respondent_id, field_name),
  FOREIGN KEY (respondent_id) REFERENCES respondents(respondent_id),
  FOREIGN KEY (field_name) REFERENCES fields(field_name)
);

CREATE TABLE client_labels (
  respondent_id TEXT PRIMARY KEY,
  status INTEGER,
  markers TEXT,
  is_client_discard INTEGER,
  label_source TEXT NOT NULL
);

CREATE TABLE agent_judgments (
  respondent_id TEXT PRIMARY KEY,
  agent_judgment TEXT,
  agent_score REAL,
  ml_score REAL,
  converging_family_count INTEGER,
  evidence_families_json TEXT,
  primary_removal_reason TEXT,
  agent_justification TEXT
);

CREATE TABLE evaluation_results (
  respondent_id TEXT PRIMARY KEY,
  truth_label INTEGER NOT NULL,
  predicted_discard INTEGER NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('TP','FP','TN','FN'))
);
```

Add run-specific tables only when they have a defined owner and are documented in `schema_summary.md`.

## Query Standards

- Include the final SQL alongside any reported metric.
- Prefer named CTEs over nested subqueries.
- Use `COALESCE` when nulls affect counts or rates.
- Cast numeric text before ordering or thresholding.
- Sanity check every metric against the confusion matrix.
- Treat surprising numbers as a reason to inspect data quality before reporting.

## Visualization And Reporting

When creating charts from SQLite outputs:

- Use colorblind-friendly palettes.
- Label axes with units.
- Use chart titles that state the finding.
- Save chart source data as CSV beside the chart.

## Reusable Knowledge

After a run, update the relevant skill reference or run report only with reusable findings:

- New field-role mappings.
- Survey-specific quota or brand-funnel patterns.
- Data quality issues that recur across workbooks.
- SQL patterns that should become standard checks.

Do not persist one-off row findings as permanent skill rules unless they survive accepted-row counterexamples.
