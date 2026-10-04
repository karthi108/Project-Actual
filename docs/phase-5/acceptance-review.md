# Phase 5 acceptance evidence: Local Qwen Model Gateway

Status: Phase-5 engineering gates satisfied on 2026-10-05. User acceptance is separate.
Binding accepted milestones are Phases 0 `4e06cc6`, 1 `5b6116a`, 2 `fc6d396`,
3 `d2a7544` and 4 `7deff65`. The focused Phase-5 commit is identified in Git history
rather than embedded in its own content. No Phase-6 implementation is included.

## Delivered boundary

The [usage guide](README.md), [design](design.md) and
[ADR 0006](../adr/0006-local-model-gateway.md) describe a provider-independent
`ModelGateway`/`ModelProvider`, one `OllamaQwenProvider` and one neutral
`synthetic_probe:v1` capability. The capability owns strict input/output contracts,
instructions and versions; the adapter owns discovery and HTTP transport. Accepted
Career/application/domain/persistence/API source and semantics remain unchanged.

The supported diagnostic takes no arguments, files or free-form prompts. Its explicitly
synthetic input contains only a bounded tuple of color enum values. There is no
CareerLab-to-prompt mapping, evaluator loader, generic chat/AI HTTP endpoint or
professional-data intake. Oracle objects, manifests, unchecked extra fields and raw
text fail admission before inference. Model output cannot update domain records,
verify evidence, authorize an action or invoke tools. Schema-valid output is explicitly
an untrusted `Proposal`, not a factual or business-valid result.

Configuration restricts explicit-port HTTP to literal loopback, with `localhost`
canonicalized without DNS. An explicit installed-Qwen allowlist and synthetic mode
are required. Proxy environment, redirects, cloud resolution, tools, retries and
repair are disabled. Before any prompt, Ollama must report cloud disabled, supported
server 0.34.3, an installed local GGUF Qwen model/digest and completion capability.
The request uses an explicit `:local` selector, schema `format`, non-streaming
generation, thinking/truncation/context shifting disabled and bounded requested options.

One total timeout includes discovery and response reading. Actual response bytes,
JSON depth, Unicode, duplicates, finite values and strict Pydantic output are checked.
Empty, truncated, wrong-model, tool-bearing and malformed results fail with safe codes.
Logs contain correlation/configuration/outcome metadata only. Prompts/results are
memory-only; no model-run table, event or archive is introduced.

## Local environment and decisions

Read-only inspection found Ollama 0.34.3 on `127.0.0.1:11434`, three installed Qwen
models and approximately 16 GB system RAM / 4 GB NVIDIA GPU memory. The configured
default `qwen3:4b-instruct` occupies about 2.5 GB; `qwen3.5:4b-q4_K_M` occupies
3.4 GB and adds unused vision support; `qwen3:8b` occupies 5.2 GB. This is a footprint
choice for plumbing, not a capability-quality comparison or GPU-residency guarantee.

The existing shared server reported cloud enabled. The binding Phase-0 privacy rule
requires cloud disabled, so the direct launcher refuses it with
`local_privacy_required`, without submitting a prompt. Its running processes/configuration
were left intact. Live acceptance used an ACTUAL-owned temporary hidden server on a
separate loopback port, with process-scoped `OLLAMA_NO_CLOUD=1`, minimized environment,
debug/body logging disabled, `OLLAMA_NOPRUNE=1`, existing installed weights and
`keep_alive=0`. No model was downloaded or shared server reconfigured.

The owned listener's exact PID/interface and cloud-disabled status were checked.
Four TCP samples during each recorded network-observed run covered the server and
its descendant runner processes; no non-loopback connection was observed. Sampling
does not exclude transient connections, UDP/DNS or compromised-server behavior and
does not constitute an egress firewall or complete information-flow proof.

## Concrete review corrections

- Frozen objects can still be forged by trusted Python code. Nested generation
  settings, provider identity/reply and capability/input are revalidated at boundaries;
  invalid timeout/context/output limits cannot bypass configuration checks.
- A rejected forged identity must not be used in a failure log. Logs now derive labels
  only after validated reconstruction, with canary tests for invalid/private values.
- Pydantic dumping can discard unchecked extra attributes. The gateway rejects extra
  raw input fields before serialization, rather than silently dropping evaluator data.
- Ollama 0.34.3 returns the exact requested `:local` name. The adapter accepts only the
  configured tag or that exact selector, normalizes the canonical identity and preserves
  the wire name separately. It does not accept arbitrary aliases or another model.
- Generic metadata must not force future providers to invent a digest/server version.
  Shared records represent unavailable details as explicit `None`; supplied details
  stay validated. The Ollama adapter still requires and records both actual values.
- Duplicate new test basenames collided with accepted API tests during combined
  collection. Only new files were renamed; all accepted tests were preserved. Final
  collection contains 938 cases. Focused tests and an earlier 937-case run were not
  substituted for the final interpreter evidence.

## Checks actually run

Host: Windows/PowerShell, uv 0.11.7, Python 3.14.7 and 3.13.1. Complete regression
suites used isolated official PostgreSQL 18.6 with the accepted immutable image
`postgres@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722`.
The accepted harness publishes ephemeral loopback ports, generates ignored credentials,
migrates per-test disposable schemas and cleans up only its identity/label-checked
container. SQLite did not replace database integration. Tests require an explicit
disposable database and do not silently skip. Normal suites never invoke Qwen.

| Check | Final evidence |
| --- | --- |
| Locked dependency/interpreter installation | Existing HTTPX2 2.13.1 promoted to runtime; all prior pins preserved; no SDK/framework/paid-provider package; 38 locked packages, 37 installed on Windows |
| Ruff lint | All source/tests/migrations plus live helper passed |
| Ruff formatting | 84 source/test/migration Python files plus one live helper already formatted |
| Strict mypy | Passed for 56 source/migration/helper files |
| Complete Python 3.14.7 suite with real PostgreSQL | **938 passed**, 133.32 seconds |
| Complete Python 3.13.1 suite with real PostgreSQL | **938 passed**, 139.24 seconds |
| Gateway/capability tests | Strict input/output, metadata preservation/availability, UTC clocks, deterministic serialization, malformed/invalid/boundary cases, unknown capability, cancellation/deadline, no repair/retry and safe logs |
| Ollama transport/config tests | Exact schema/no-tools request, local/cloud/model gates, missing/load/unavailable failures, response identity, bounded raw streams, malformed/oversize/truncated data, whole-call slow-drip timeout and no proxies/redirects/retries |
| Diagnostic/privacy tests | No prompt arguments, safe configuration errors, fixed synthetic input, child environment excludes database/API credentials and disables debug retention/pruning |
| Genuine Qwen smoke on Python 3.14.7 | Validated proposal through installed local Qwen; network-observed gateway duration 11.93 seconds; four samples, no non-loopback TCP observed |
| Genuine Qwen smoke on Python 3.13.1 | Validated proposal through the same installed model; gateway duration 13.81 seconds; four samples, no non-loopback TCP observed |
| Direct diagnostic against existing shared server | Safe nonzero refusal with `local_privacy_required`; fixed metadata log, no prompt/result output |
| Migration head and offline PostgreSQL SQL | Single unchanged `0001_career_persistence` head; upgrade and head-to-base downgrade compiled |
| Accepted migration/storage/API tests | Full suites include bootstrap/repeat/downgrade/re-upgrade, drift/installed guards, transactional rollback/concurrency, provenance and synthetic/private/deleted API gates |
| CareerLab generation and offline verify on both interpreters | Eight public development cases; same new environment identity; all input/oracle hashes preserved |
| Accepted file audit | All 114 files outside four authorized root/configuration edits preserve accepted Git content |
| Phase-4 generated OpenAPI | Exact accepted canonical schema hash preserved |
| Final docs/artifact/whitespace/cleanup audit | Local links and example syntax verified; scoped staging and manifest-source/input audit passed; no private/oracle/held-out files staged; owned processes/containers/private files removed |

The final suite consists of all 770 unchanged Phase-0–4 checks and 168 new model checks:
76 gateway/probe, 88 provider/configuration/architecture and four diagnostic checks.
Fake providers and injected local transports make failure tests deterministic; genuine
Ollama/Qwen acceptance is separate. These are engineering tests and assistant reviews,
not an independent security certification or an AI accuracy/F1 evaluation.

The standard harness completed the final Python-3.13 suite after the metadata refinement.
Python 3.14 was then rerun against a fresh disposable database using
`scripts/verify_phase5.ps1 -PythonExecutables @('C:\Python314\python.exe')` so its
complete evidence also covers the last added test and final source. No test was skipped.
Harness-owned PostgreSQL resources and credential files were removed by its cleanup;
the unrelated project container and original shared Ollama process identities remained
unchanged. No temporary live server or model runner was left running.

## Reproducibility identities

Selected local model: `qwen3:4b-instruct`; wire response:
`qwen3:4b-instruct:local`; server: `0.34.3`; family: `qwen3`; quantization: `Q4_K_M`.
Preflight-observed catalog digest:

```text
0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0
```

Both recorded smoke results used `synthetic_probe:v1`,
`actual-probe-output-v1`, context 4096, maximum output 128, temperature zero, seed 42
and a 120-second total deadline. Their shared schema and prepared-prompt identities are:

```text
schema: 87d015c04de87e41b6a3786d13139c223fa726601ce71273bc934be3a11c53e8
prompt: 10146567b04f452986d7dd1c8d81b9ba559283ffd3004fd9f92a7c9346ddb6ae
```

Each result carries its own correlation ID, aware UTC start/finish, elapsed duration,
configured/response model, requested settings and available provider details. Tags
are mutable; the catalog digest observed before a call does not attest the exact
loaded weights under concurrent retagging or host tampering. Requested options do not
prove every effective server default. Similar structured successes do not demonstrate
byte-identical inference, factual correctness or determinism.

The [new model environment manifest](../../datasets/manifests/careerlab-model-env-v1.json)
has identity:

```text
a63a2e6c15549c2d5ba8f95c9b5862edce34bcc0f50e4078c4c979185542ac6e
```

It binds the current project/lockfile environment while preserving all eight fixture
records, their lineage metadata and sixteen input/oracle hashes. All four historical
manifests and accepted source, tests, migrations, docs and public inputs remain intact.
No accepted snapshot expectation or evaluator answer was changed to pass a test.
Validation/locked-test datasets remain unmaterialized; no individual held-out case was
generated, inspected or tuned. Model inference uses purpose-built enum fixtures only.

## Limitations and next-phase boundary

This proves local inference plumbing and structural rejection behavior. It does not
prove Job Intelligence, hiring quality, evidence truth or professional usefulness.
No job requirements/fit scores, CV tailoring, application generation, real-data input,
Career AI API, connector, tool/effect executor, workflow runtime, NEXUS, Redis, Temporal,
cloud deployment, paid API, frontend or Phase-6 behavior is implemented.

Only reviewed Ollama 0.34.3 and three inspected installed Qwen identifiers are supported.
Status/local-selector controls are version-sensitive; other server versions fail closed
pending compatibility review. The Windows live helper is not a portable deployment or
permanent service manager. Trusted server/OS operation is required. Local binding and
reported cloud status do not authenticate callers or protect against host compromise.

Timeout bounds ACTUAL's asynchronous wait; it cannot guarantee immediate cancellation
of Ollama's computation. Payload/token caps are not a load/denial-of-service or GPU
capacity certification. No retry means transient failures require explicit caller action,
with no silent attempt to obtain a passing sample for evaluation.

Raw content is memory-only by default. Console capture and the separately operated
Ollama service have their own retention responsibilities; automatic seven-day diagnostic
purging is not implemented. Content hashes can be linkable. Expanding the capability
registry to free text or real data requires new privacy, semantic, provenance and access
gates; this phase does not grant that permission. Phase 6 requires a new user request.
