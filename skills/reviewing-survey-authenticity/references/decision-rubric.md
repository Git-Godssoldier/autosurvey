# Decision Rubric

Use five tiers. Keep client rejection probability and authenticity risk conceptually separate.

## Tier 1: Strong Keep

The full response chain is coherent, grounded, and human-plausible. Minor imperfections may exist, but they support ordinary human behavior or are irrelevant.

## Tier 2: Keep With Note

Some weak anomaly appears, but the row has enough respondent-specific grounding or coherent chain evidence to keep. Use this tier to preserve guardrails.

## Tier 3: Human Review

The row has material concerns, but evidence is ambiguous or concentrated in one family. The respondent should not be excluded without a human check or more context.

## Tier 4: High-Risk Review

Multiple independent evidence families point toward fabrication, automation, or bad-faith responding, but one unresolved protective explanation remains.

## Tier 5: Exclude Candidate

The full chain has convergent, independent evidence of inauthenticity, fabrication, automation, route abuse, synthetic content, or respondent bad faith. The rationale must explain why accepted-row guardrails do not save the case.

## Decision Rule

Only Tier 5 is the discard recommendation. Tiers 1 through 4 remain outside the discard set, although Tiers 3 and 4 can count toward client review workload.

## Evidence Standard

Do not exclude for one weak signal. Require convergence across independent families such as semantic contradiction plus generic open ends plus timing-content implausibility, or route incoherence plus duplicate synthetic cluster plus lack of human grounding.
