# Deterministic process discovery

IMPLEMENTED; canonical acceptance PENDING.

Discovery groups owner-scoped semantic events by explicit session, deduplicates source identities and orders only by observed occurrence time. Conflicting identities, mixed session actors and ambiguous equal-time ordering fail; arrival order never invents a causal sequence. Inputs and session counts are bounded.

The report contains full observed variants, repeated contiguous sequences of length 2–4, transition counts, branch points, observed returns/rework, session elapsed time and per-activity elapsed-gap summaries. These observations produce no executable loop, company policy or activation. Gaps between observations are elapsed time, not human active time; sorting bottlenecks cannot prove a delay was caused by the preceding activity.

Three public synthetic development sessions have separately asserted ground truth: two base traces, one rework variant, fifteen events, two branch points, one observed return, and elapsed durations 40/40/50 seconds. The observed compare-step mean gap is 12.5 seconds. Tests cover shuffled arrival, duplicate/conflicting identity, ambiguous order and owner scope.

The ACTUAL domain uses ordinary bounded counters/statistics, with no PM4Py dependency or licensing claim. Real event completeness, clock accuracy, causality, process coverage and performance require canonical evidence. Shared development traces are not an independent held-out set.
