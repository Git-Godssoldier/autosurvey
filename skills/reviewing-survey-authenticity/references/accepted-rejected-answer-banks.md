# Accepted And Rejected Answer Banks

These examples are labeled development evidence. Use them to improve future unannotated runs and to calibrate semantic distinctions. Do not use a dataset's own labeled answer bank during an active sealed benchmark for that same dataset.

Status labels remain client decisions, not proof of fraud. Treat these banks as examples of the client's cleaning boundary and contrast them with accepted-row guardrails.

## Delta Water Filtration Lessons

Delta showed that raw speed and shortness were weak separators. Accepted rows also included fast and short answers. The clearest client-rejection signals were field-invalid answers and cross-respondent template behavior.

### Rejected-Leaning Patterns

Repeated open-end templates are strong when the sentence is uncommon and appears across supposedly independent respondents. The answer can look fluent in isolation but becomes suspicious in the cohort.

Examples from rejected rows:

- Rows `808`, `811`, `813`: outro says `Attitudes toward tap water improvement solutions`.
- Rows `809`, `810`: outro says `Buying behavior for residential filtration products`.
- Rows `776`, `778`: same long outro about `faucet-mounted filtration devices` as a `convenient solution`.
- Rows `1054`, `1061`: same `q14` phrase: `Honestly the water felt a bit harsh on my skin and hair so I thought of fixing it`.
- Rows `674`, `681`: same `q14` answer about odd taste or fragrance.

Wrong-topic or wrong-dimension outros are stronger than generic correct summaries.

Examples:

- Row `1315`: outro says `This survey was about Hair products`.
- Rows `679` and `751`: outro says `Increasing personalization in order to have more pertinent recommendations`.

Nonresponsive purchase-prompt answers are hard invalidities.

Examples:

- Row `1327`: `q14` says `good morning my friend I hope`.
- Row `1329`: `q14` says `Good night my friend hope you're`.
- Row `463`: `q14` says `The only thing to do with it and I'm sure you will enjoy`.
- Row `265`: `q14` says `Nothing good`.

Survey-meta or praise-like outros are supporting evidence, not standalone exclusion evidence. They become meaningful when paired with another hard invalidity, template behavior, or cohort risk.

Examples:

- Row `1334`: outro says `i love this survey`.
- Row `1340`: outro says `It was very easy and fast. I really enjoy it.`
- Row `463`: outro says `Very much for your time`.

Missing supplier/source is a cohort-level risk signal, not semantic proof. In Delta, missing supplier/source had a materially higher rejected rate than named suppliers such as PrimeInsightsGroupLLC-API, Attapoll, and MakeOpinionGmbH-API.

### Accepted-Leaning Guardrails

Do not punish speed alone on Delta-style surveys. Fast respondents were often accepted, and rejected respondents were not simply the fastest group.

Do not punish short outros alone. Accepted rows often contained very short but correct answers. Shortness becomes meaningful when it is nonresponsive, duplicated, wrong-topic, or paired with another issue.

Generic but correct answers such as `water filtration systems` can be accepted unless they are part of a duplicated/template cluster or paired with another hard invalidity.

### Transferable Rule

A row becomes client-rejection-like when a locally invalid answer or repeated/template open end appears, especially when paired with survey-meta language, wrong-topic comprehension, missing-source cohort risk, or another independent mechanical concern.

The accepted-row opposite is equally important: a generic but correct answer should remain protected when it answers the field, is not part of a suspicious duplicate cluster, and the rest of the chain is coherent.
