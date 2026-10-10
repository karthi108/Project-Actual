# Isolated historical replay

IMPLEMENTED; canonical acceptance PENDING.

Problem: candidate workflows need reproducible comparison before activation. WorkLab supplies five explicitly synthetic public development observations and a separate evaluator answer module. The runtime imports neither fixture generation nor evaluator answers. No validation or locked-test set is claimed or materialized.

Replay uses the same bounded step executor with transient state and virtual time. Historical policy observations affect only simulated control flow. Replay/shadow constructors reject provider handles; the dispatch boundary also checks mode. No provider, model or real effect can be invoked. Human waits become explicit escalation results. Closed workflows and trigger inputs are revalidated before replay.

`python scripts/evaluate_worklab.py` measures expected-status/branch matches, completed cases, escalation, failures, policy denials and invalid tool calls. Unsupported AI claims are unmeasured (`null`) because no inference is executed. The checked development report has five expected-status and branch matches, two completions, one escalation, two deliberate failures, one policy denial and zero provider calls. This is deterministic development replay, not new live, held-out or real-world accuracy evidence.

Trade-off: pure simulation validates graph/control behavior with no database/provider latency claim. Durable crash/approval/idempotency evidence remains in separate real-PostgreSQL tests. These shared development examples cannot become an independent held-out set by partitioning them.
