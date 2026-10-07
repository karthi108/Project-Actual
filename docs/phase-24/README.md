# Phase 24 — Security hardening

Status: IMPLEMENTED for the synthetic boundaries; office checks below are provisional. Canonical security validation and acceptance remain PENDING.

Stored JSON is untrusted even when it parses. Workflow reads now compare payload owner, run/trigger identity, revision and trigger digest with relational columns; definition reads also check name/version metadata. A worker cannot claim a mismatched record. Trigger fields are ordered before new event hashing, so changing field order cannot manufacture another business event.

The dispatch check now compares the complete approval (including reviewer, expiry and reviewed-content digest) with its approved audit seal. Permission, activation, workflow/content pins, lease, revocation and stable intent checks still apply immediately before dispatch. The seal is a consistency check across records, not a signature or protection from a database administrator rewriting both records. Legacy provisional effect approvals with the earlier access-only seal are refused: preserve their audit, cancel the old run and prepare a fresh exact review. Accepted Career reviews and migrations are unchanged.

Explicit workflow/approval/activation/shadow migrations verify reflected columns, types, nullability, primary keys and unique constraints. Unknown drift is rejected instead of being marked migrated. Migrations do not guess how to repair drift. Connector reads reject duplicate arguments before provider invocation.

## Adversarial coverage

| Threat | Executable evidence / boundary | Limit |
| --- | --- | --- |
| Malicious jobs/documents; model promotion of fake evidence | `test_intelligence_isolation.py`, `test_source_extraction.py`, profile projection and preparation tests | Bounded structured/paste-only inputs; no arbitrary PDF parser or independent truth certification |
| Model secrets/tool authority | Accepted `tests/models` isolation, schema, diagnostic and timeout checks | Workflow AI steps remain unavailable; no inference-tool executor |
| Cross-object access and forged actor/workspace | Accepted API/application/persistence scope tests; stored-run identity tests | Synthetic loopback API is explicitly unauthenticated; real intake remains disabled |
| SSRF/arbitrary URLs/OAuth scope abuse | Registered connector resource literals; `test_connectors.py`, `test_nexus.py` | No OAuth capability, arbitrary URL fetch or real provider adapter; real redirect/DNS/scope review pending |
| Tool-output injection | Closed typed connector output; hostile output remains data | No instruction can alter registry, permission or approval |
| Stale/replayed/revoked approval; changed workflow | `test_effect_approval.py`, `test_activation.py`, `test_workflow_security.py` | Exact fake action review; no real-account guarantee |
| Tampered IR/stored identity/schema | `test_ir.py`, `test_workflow_security.py` | Trusted operator/database administrator can still rewrite all records |
| Duplicate side effects/crash/uncertain acknowledgement | `test_effect_approval.py`, `test_workflow_reliability.py` | Durable fake provider evidence; actual provider recovery/idempotency semantics pending |
| Capture/voice privacy | `test_teach.py`, `test_voice.py` | Explicit synthetic harness only; no native capture or real microphone |

Run the pure workflow/model tests and the PostgreSQL workflow, approval, activation, shadow, reliability and security tests on Python 3.13 and 3.14. These are adversarial regression checks, not a penetration-test certification. Final office results are recorded in the debt register.

Synthetic labels cannot detect deliberately mislabeled personal data. Host/origin/CORS checks cannot authenticate a local caller. No service is opened to a shared/public network, no real secret or company system enters this slice, and no arbitrary generated code is executed.
