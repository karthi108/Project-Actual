# Phase 5 design: typed local inference proposals

Status: implementation design under the user's Phase-5 request. Accepted milestones
are Phase 0 `4e06cc6`, Phase 1 `5b6116a`, Phase 2 `fc6d396`, Phase 3 `d2a7544` and
Phase 4 `7deff65`. Actual check outcomes are recorded separately in
[acceptance evidence](acceptance-review.md). No Phase-6 behavior is included.

Binding decisions come from [architecture](../phase-0/architecture.md),
[privacy](../phase-0/privacy.md), [threat modeling](../phase-0/threat-model.md),
[evaluation](../phase-0/evaluation-strategy.md) and the accepted Core, persistence and
HTTP boundaries. [ADR 0006](../adr/0006-local-model-gateway.md) records this addition.

## Problem and smallest solution

ACTUAL needs to request typed inference without letting application capabilities
depend on Ollama's transport, mutable tags or error shapes. It also needs to reject
invalid generated content without converting schema validity into professional truth.

Use a small gateway, a provider protocol, one Ollama implementation and one explicitly
versioned neutral capability. The new composition root is a fixed local CLI diagnostic;
the Phase-4 API and CareerService remain unchanged. No new database schema, authority
fields, model-specific domain records or general-purpose chat API are needed.

The path is:

```text
synthetic_probe:v1 + ProbeInput
    -> ModelGateway
    -> ModelProvider protocol
    -> OllamaQwenProvider
    -> cloud-disabled loopback Ollama / installed local Qwen
    -> strict JSON + Pydantic validation
    -> Proposal[ProbeOutput] + InferenceMetadata
```

The proposal has no persistence or effect authority. An output schema proves only that
the resulting data satisfies its structural contract. Even a well-shaped incorrect
token count is still a structurally valid proposal; Phase 5 introduces no semantic
Career evaluator or downstream mutation from model output.

## Responsibilities

| File | Owns |
| --- | --- |
| `src/actual/models/contracts.py` | Frozen provider-independent generation settings, identity, prepared transport input, provider reply, protocol, registered capability and proposal metadata |
| `src/actual/models/gateway.py` | Exact capability/input admission, canonical preparation, bounded invocation, strict result validation, proposal construction and safe metadata logging |
| `src/actual/models/codec.py` | Bounded strict JSON decoding and canonical encoding |
| `src/actual/models/errors.py` | Fixed content-free model failure codes |
| `src/actual/models/config.py` | Explicit synthetic mode, local destination/model allowlist and bounded configuration |
| `src/actual/models/ollama.py` | Ollama preflight, HTTP protocol, local selector, provider response limits and safe transport failures |
| `src/actual/capabilities/probe.py` | Neutral input/output contracts, instructions and capability/schema versions |
| `src/actual/models/__main__.py` | Local fixed-input diagnostic composition and metadata-only console output |
| `scripts/verify_phase5_live.py` | Genuine probe using an owned temporary local-only Ollama child and existing weights |
| `tests/models/` | Deterministic gateway, configuration, transport, privacy and dependency-boundary checks |

The provider has no Career reasoning, profile import, SQL dependency, filesystem
mutation or tool executor. The gateway has no Ollama/HTTP dependency. Core, Profile,
Career, the current application service, persistence and API retain accepted meaning.
The capability registration is trusted Python configuration, not a client-supplied
plugin or arbitrary prompt mechanism.

## Typed request and output boundary

A `Capability` binds name/version, expected input/output model types, schema version
and fixed instructions. `ModelGateway.run(capability, input)` admits only the exact
registered capability object and input model type. It revalidates frozen configuration
and input fields before serialization; subclasses and extra unchecked fields do not
silently expand the input surface.

The shipped `synthetic_probe:v1` input has explicit `synthetic=True`,
`actual-probe-input-v1` and at most eight color enum values. Its closed output requires
`actual-probe-output-v1`, the `synthetic-probe` marker, an integer count from 0 to 8 and
a first-token enum. Instructions live in the capability module, rather than HTTP
handlers or provider code.

Canonical JSON uses sorted keys, compact separators, UTF-8 and finite numbers. Model
output is decoded as a strict object, then validated with the declared strict, closed
Pydantic output model. Unknown keys, missing fields, wrong types, invalid enums, invalid
Unicode, duplicate keys, non-finite values, deep nesting and limits fail closed. No
free-form fallback, markdown stripping, field coercion or schema repair is implemented.

Model types are independent of accepted `actual-core-v1` records. They do not weaken
Core's recursive version checks or add provider fields to domain contracts. No
`ModelRequest`/`ModelResponse` naming symmetry is required: the typed capability/input
and `Proposal` are the useful caller boundary; prepared input/reply serve the adapter.

## Local provider preflight and protocol

Configuration permits only explicit-port HTTP endpoints on `127.0.0.1`, `localhost`
or `::1`. `localhost` becomes `127.0.0.1` without DNS. External destinations,
credentials, URL paths other than the root, queries and fragments fail configuration.
HTTPX2 2.13.1, already used in accepted API tests, becomes a runtime dependency;
no separate Ollama SDK or agent framework is needed. Each operation uses a fresh
non-proxied client, disables redirects and transport retries, and closes the client.

Before sending capability instructions/input, the provider checks:

1. `/api/status` reports `cloud.disabled` exactly true.
2. `/api/version` is the reviewed **0.34.3** server version.
3. `/api/tags` has exactly one matching installed allowed tag, a valid digest, local
   GGUF Qwen metadata and no remote host/model fields.
4. `/api/show` for the explicit local selector has consistent family/quantization,
   local metadata and completion support.

The adapter uses `/api/chat` with schema in `format`, system instructions and a
canonical user-data message. It requests `stream=false`, `think=false`,
`truncate=false`, `shift=false`, `keep_alive=0`, fixed temperature/seed and bounded
context/output settings. The local selector prevents implicit cloud-model resolution.
Tools and arbitrary HTTP/function requests are absent.

Each response must have accepted JSON media/encoding, bounded declared/actual bytes
and valid strict JSON. Generated responses must be complete, report a stop rather
than output truncation, identify the expected model and contain an assistant message
without tool calls or nonempty thinking. Only its content and bounded provider
metadata reach the gateway. Raw provider errors never become application errors.

Ollama may echo the explicit `:local` selector in its model field. The adapter accepts
only the configured base tag or that exact tag plus `:local`; it returns the canonical
base identity while retaining the reported echo in `ProviderReply.reported_model`.
Proposal metadata records that echo as `response_model`. Other aliases remain errors.

Ollama documents schema-constrained output and subsequent Pydantic validation in
[Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs), and its
[Chat API](https://docs.ollama.com/api/chat) describes chat request/response fields.
The experimental status/local-selector and truncation/context-shift behavior is tied
to the inspected [0.34.3 server source](https://github.com/ollama/ollama/blob/v0.34.3/server/routes.go)
and [API types](https://github.com/ollama/ollama/blob/v0.34.3/api/types.go). Unknown server
versions fail closed until those assumptions are reviewed and tested.

## Timeout and failure policy

One total deadline includes preflight, model loading/inference and response reading.
Gateway and provider use bounded asynchronous operations; per-read HTTP timeout alone
would let a slow-drip response evade the intended limit. The default is 120 seconds,
with a configured maximum of 300 seconds. Connect waiting has a five-second bound
within the total deadline.

There are no retries. Connection failure, timeout, absent model, model-load failure,
HTTP/provider failure, privacy precondition failure, invalid envelope, invalid output
and limits are distinguishable fixed `FailureCode` values. Failed inference returns
no proposal and cannot partially save Career state: the gateway has no repository or
transaction dependency. Cancellation stops ACTUAL waiting but may not immediately stop
the provider's computation. A retry would be a new manually initiated operation.

Resource bounds are 4096 UTF-8 input bytes, 8192 instruction bytes, 16384 schema bytes,
32768 generated-content bytes, 131072 bytes per provider response and JSON nesting
depth 32. Requested context ranges from 512 to 8192 tokens, and requested output from
16 to 512. These configuration values are not an independent tokenization or GPU
memory proof. Silent input truncation and context shifting are disabled.

## Metadata, reproducibility and logging

Every accepted proposal records server-generated request ID; configured provider,
model and local endpoint; requested generation settings; validated raw response identity;
observed catalog digest, server version, model family and quantization; capability
identifier, output schema version/hash and prompt hash; aware UTC start/finish; and
monotonic duration. `proposal_only=True` preserves the intended interpretation.

The provider-independent reply and metadata permit an explicit `None` for model digest
or server version when unavailable; JSON serialization preserves that absence as
`null`. Optional information is not fabricated to satisfy an Ollama-shaped abstraction.
The current Ollama adapter still requires and records its observed catalog digest
and reviewed server version on every successful call.

The prompt hash binds canonical instructions and serialized input; it does not retain
their contents. The digest identifies what the catalog reported before invocation,
not an atomic attestation of the exact loaded weights. A model tag can be changed
between catalog inspection and inference, and binaries/templates/server defaults can
also affect results. Metadata permits useful run identification without claiming a
fully reproducible immutable execution environment.

Canonical preparation, hashes and metadata serialization are deterministic for the
same supplied data. New request IDs/times intentionally differ. Temperature zero and
seed 42 are conservative generation settings, not proof of byte-identical model output.
No accuracy/F1, hiring suitability, generation determinism or usable p95 is claimed.

Run logs allow only request ID, validated provider/model/capability labels, duration,
status and fixed error code. No prompt, response, endpoint, input validation values,
stack trace, credential or raw provider exception is logged. Returned metadata may
include endpoint/hashes, but raw prompts/results are neither archived nor automatically
persisted. Logging has no exporter, file backend or automatic retention scheduler.
Future persistence/debug-content logging needs its own privacy decision.

## Privacy and evaluation isolation

The accepted Phase-0 rule requires a local destination/model allowlist and cloud-disabled
server. The inspected shared server does not meet the latter precondition. ACTUAL
does not silently edit its configuration or restart it; the supported live helper
sets `OLLAMA_NO_CLOUD=1` only in its owned temporary server process. The
[official FAQ](https://docs.ollama.com/faq) explains that server configuration must take
effect before relying on local-only mode.

During the live call the helper samples established TCP peers for the owned server
and all discovered runner descendants. It fails on an observed non-loopback peer and
reports the number of samples without printing addresses. This is limited observed
traffic evidence: sampling can miss short-lived TCP connections and does not inspect
UDP/DNS or enforce a network firewall. It is not proof of complete information-flow
isolation or safety of a compromised local process.

The current runtime input permits only a fixed vocabulary of synthetic tokens. There
is no job/CV/document/profile input, raw-text diagnostic, dataset reader, database
reader or CareerLab mapping in the inference path. Oracle, authoring bundle and
membership/manifest objects cannot satisfy its exact input contract; extra fields
cannot smuggle their contents into prepared inference. Evaluation-only fixtures stay
outside runtime imports, prompts and mounts. This is a deliberate Phase-5 minimization,
not a generic redaction filter for future personal data.

The local OS/operator and Ollama process remain trusted. Reported server status is
configuration evidence, not packet-level proof or protection from malicious software.
Real personal access stays disabled under accepted Phase-4 restrictions. Future
synthetic Career capabilities must establish an observable-only mapping and deny
evaluator metadata again when such a mapping actually exists.

## Acceptance methodology

Require actual recorded evidence for these gates before committing:

1. Internal gateway/protocol is provider independent; one local Ollama/Qwen provider
   and one neutral versioned capability are usable without changing domain contracts.
2. Valid typed results carry correct metadata and remain proposals. Strict malformed,
   empty, truncated, wrong-schema, extra-field, enum/type and size cases fail closed.
3. Destination/model/cloud guards, unavailable/missing/unloadable model mapping,
   total timeout, slow response, metadata provenance and no-retry policy are tested.
4. Runtime inference excludes evaluator data, real personal input and effect/tool
   authority. Metadata-only logging and safe failures are demonstrated.
5. A genuine local installed-Qwen call produces a schema-validated result through the
   gateway with verified local-only server/process setup; it is reported as plumbing.
6. All accepted regressions, real PostgreSQL/migration tests, Python 3.13/3.14 checks,
   lint, formatting and strict typing pass. Normal tests do not require live Qwen.
7. Accepted source/canonical artifacts and all CareerLab record hashes are preserved;
   the changed environment receives its own manifest without regenerating held-out data.
8. Documentation accurately records limitations and actual results, private data/model
   weights are excluded from Git, and one focused local commit leaves a clean tree.

## Known limitations

This phase establishes an inference boundary, not Job Intelligence. It provides no
extraction, fit assessment, CV tailoring, cover letter, application generation,
material verification, workflow execution, connectors or AI HTTP use cases.
The probe's structural result does not prove semantic correctness or resistance to
Career prompt injection; those capabilities are absent and need later evaluation.

Support is deliberately limited to the three inspected local tags and Ollama 0.34.3.
The isolated live helper is Windows-specific and reuses local installed weights; it
is not model installation, a deployment supervisor or a long-running service manager.
Neither helper nor gateway implements an OS network sandbox, protects a compromised
host or guarantees computation stops immediately on timeout. Existing Ollama service
logs/OS console capture remain separate operator-controlled boundaries.

There is no model-run persistence, automatic deletion/rotation, immutable loaded-model
attestation, concurrent model-capacity scheduler, benchmark, fallback provider or
paid service. Low temperature, seed and catalog digest improve run identification but
do not guarantee identical inference. No real-data access or automatic Phase-6 work
is authorized by this implementation.
