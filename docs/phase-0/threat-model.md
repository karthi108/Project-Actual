# Threat model v0.1

Status: design review. No control below has been implemented or tested.

## Assets and trust boundaries

Assets are personal records/CVs, evidence integrity, drafts, credentials when introduced, application state, review/audit records and the user's authority. The local OS account and development tools are trusted; imported material and models are not.

| Boundary | Trust transition | Required enforcement |
| --- | --- | --- |
| Browser to API | Browser requests may originate from hostile sites or forged clients | Local authentication, exact allowed Host/origins, CSRF protection for cookie sessions, request/size limits |
| API to domain/data | Request fields are untrusted, even with syntactic validity | Server-derived actor/workspace, owner-scoped lookups, transactions and domain invariants |
| Job/document to intelligence | Content may contain instructions, misleading facts or hostile markup | Treat as data, bounded input, no authority, escaped rendering |
| Model to domain | Output may be malformed, fabricated or adversarial | Closed structured schema, reference/claim validation, escalation and bounded retries |
| Application to local model | Personal data crosses into a separate process | Explicit local endpoint/model allowlist, no credentials, minimum context, cloud disabled |
| Application to files | Paths/content may escape intended storage | Generated paths, scoped access, no arbitrary path/URL intake |
| Future runtime to connector | Consequential action leaves the local transaction | Current authorization, exact approval, deduplication, audit and outcome reconciliation |

Being on localhost does not authenticate a caller. Before real personal API use, choose a simple local-owner session/pairing mechanism with secrets outside the repository; synthetic-only unauthenticated development must be explicitly isolated. Exact mechanism is finalized with Phase 4. CORS is not an authorization system.

## Threats and acceptance evidence

| ID | Failure/attack | Contract control | First required evidence |
| --- | --- | --- | --- |
| T01 | Job says to ignore rules, upgrade skills or reveal secrets | Data-only model input, no tool authority, factual output gate | Malicious CareerLab cases in Phase 1; end-to-end proposal rejection in 5-6/9 |
| T02 | Fabricated or weak evidence becomes professional truth | Explicit method/status, support scope, independent verification distinction | Invalid support and withdrawn-evidence checks in Phase 2; draft checks in 9 |
| T03 | Hostile website writes to a local API; forged owner ID | Session authentication, Host/origin checks, CSRF as applicable, scoped resources | Unauthorized/foreign-origin/wrong-owner tests in Phase 4 |
| T04 | Container/model ports exposed on LAN or cloud model selected | Explicit loopback publishing, internal DB, endpoint/model allowlist, local-only configuration | Network/config inspection before real data in Phase 3-5 |
| T05 | CV/source/prompt/token leaks in Git or diagnostics | Private data root, ignored generated data, allowlisted logs, no secret model context | Repository and log-path inspection when storage/logs begin |
| T06 | Model returns invalid JSON, invented IDs, huge output or times out | Strict schema, resource/time limits, no unlimited repair loop, manual fallback | Bounded malformed/timeout/fake-reference tests in Phase 5 |
| T07 | Imported markup/script executes in UI | Escaped plain-text rendering, no raw HTML trust | Browser tests with hostile content in Phase 8 |
| T08 | Arbitrary URL/path intake causes SSRF or file escape | Paste-only intake initially; registered destinations and safe storage | Intake/path checks with API; later connector redirect/DNS/path tests |
| T09 | Approval is reused after document, destination or policy change | Content-bound immutable approval, recheck at dispatch | Stale/replayed/revoked approval tests before any external write |
| T10 | Retry, concurrent worker or workflow upgrade sends twice | Stable business intent, atomic reservation, remote idempotency/reconciliation | Crash/concurrency/acknowledgement-loss tests before any external write |
| T11 | Shadow/replay accidentally invokes live effects | Effect adapters unavailable/substituted, execution mode enforced below model | Effect spy/sandbox tests before replay/shadow introduction |
| T12 | Deletion leaves derivatives, logs or restored backup data | Linked derivative invalidation, purge policy and deletion ledger | Delete/export/restore tests before persistence of personal data |
| T13 | Capture becomes covert surveillance | No capture in v0.1; explicit visible sessions, pause/stop/allowlist later | Capture privacy tests before Phase 17 |
| T14 | Audit edits are treated as trustworthy history | Append-oriented application writes, scoped storage, documented admin limit | Audit transaction/access tests as audited actions appear |

Prompt filtering/redaction is defense in depth, not proof that hostile content is safe. Isolation, least privilege and human review remain necessary. [OWASP prompt injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)

Cookie-based state-changing requests need the selected CSRF defense; origin checks are an additional control, and tokens must not be exposed in URLs/logs. [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

## Stop conditions and residual risk

Do not introduce real personal data until current storage, access, deletion and network checks exist. Do not activate external writes before authorization/approval, audit and duplicate/unknown-outcome tests. Failed extraction or unsupported assertions must escalate, not silently fall back to invented facts. Phase 12 connector work starts with scoped reads; writes stay absent/disabled until their prerequisites are demonstrated.

Malware, OS administrator compromise and a determined owner rewriting local files are outside the first release's protection. Human review can miss misleading paraphrases; provenance does not certify external truth. Synthetic cases cannot establish hiring suitability or enterprise security. Document these limits rather than calling ACTUAL secure or production-ready.
