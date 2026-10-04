# ADR 0006: Local typed inference proposals through one provider

Status: implemented within the user's Phase-5 request, subject to recorded engineering
acceptance. Accepted baselines are Phases 0 `4e06cc6`, 1 `5b6116a`, 2 `fc6d396`,
3 `d2a7544` and 4 `7deff65`. This decision adds local model infrastructure only;
it does not authorize Job Intelligence, real-data access or Phase 6.

## Decision

Introduce `ModelGateway` and a small `ModelProvider` protocol independently of Ollama.
Trusted capability definitions own typed input/output, prompt instructions and version
identifiers. The gateway validates the exact registered input, prepares canonical
bounded JSON, calls a provider once, strictly validates generated JSON and returns an
untrusted typed `Proposal` with run metadata. Existing Core, Career, Profile,
application, persistence and HTTP contracts remain unchanged.

Implement one `OllamaQwenProvider` using the supported HTTP interface through HTTPX2
2.13.1, promoted from the existing API development dependency. Do not introduce an
Ollama SDK, agent framework, tool adapter, future-provider implementation or paid API.
The provider owns transport/preflight only; capability instructions remain elsewhere.

Ship only `synthetic_probe:v1`, a closed neutral color-token capability. It supports
strict structured inference without adding job extraction, fit scores, CV generation
or any professional domain mutation. A fixed-input CLI is the composition root;
there is no AI HTTP route or arbitrary prompt/file intake. The current input vocabulary
cannot carry CareerLab oracle objects or personal prose, and runtime modules do not
read authoring/evaluator data.

Choose installed `qwen3:4b-instruct` as the configurable default because its roughly
2.5 GB installed footprint is the smallest of the three inspected local options on
the 16 GB RAM / 4 GB GPU host. `qwen3.5:4b-q4_K_M` and `qwen3:8b` remain configurable
allowlisted alternatives. This is a resource-conscious text-probe choice, not a model
quality ranking or guarantee of complete GPU residency. No download or installation
mutation is necessary.

Require loopback-only HTTP configuration, ignore proxy environment, deny redirects,
require explicit cloud-disabled status and local installed GGUF Qwen/completion
metadata, and use the explicit local selector. Target Ollama 0.34.3 only: status,
local-selector and truncation/context-shift assumptions are concrete reviewed protocol
dependencies, so unknown versions fail closed pending compatibility review.

The existing shared Ollama server reported cloud features enabled. Preserve its
installation/configuration. A separate live-verification helper starts an owned hidden
loopback child using existing weights, `OLLAMA_NO_CLOUD=1` and a minimized environment,
checks status/process binding, performs the fixed probe and stops its child. ACTUAL
refuses the shared default endpoint until the local-only prerequisite is established.

Use schema-constrained chat, strict post-generation parsing/Pydantic validation,
bounded input/response/context/output, one total timeout and no retry/repair policy.
Do not accept truncated or tool-bearing results, schema coercions or empty fallback
values. Fixed model failures contain no provider body or raw exception message.

Keep prompts/results in memory without new tables, events or archives. Log allowlisted
run metadata only. Proposal metadata records provider/model/configuration, available
catalog digest/server details, capability/schema/prompt identity, correlation ID and
timings. Catalog digests and mutable tags do not attest the exact loaded weights;
temperature zero and a seed do not establish deterministic inference.

Keep model digest/server version explicitly optional in provider-independent contracts
where another provider cannot obtain them. Ollama still requires and reports its actual
catalog digest and reviewed server version. Missing metadata is represented as `None`,
not an invented provider identifier.

## Alternatives and consequences

Direct Ollama calls inside CareerService or routes would couple capabilities to provider
transport and error semantics. A generic agent/chat framework would add unused authority
and configuration. A probe that accepts arbitrary text or entire Career snapshots would
expand privacy exposure without proving more about the gateway. Full prompt persistence
would create retention/privacy responsibilities with no accepted need.

Silently editing the shared Ollama configuration would exceed the user's installation
constraint. Relying on loopback alone would violate the accepted cloud-disable rule.
The temporary isolated server resolves both for the live acceptance check, while the
default runtime still fails closed against an unsuitable server. The helper adds no
application deployment or permanent service state.

Sample established TCP connections for the helper-owned server and runner descendants
during the live probe. Report observations without claiming that finite sampling rules
out transient TCP, UDP/DNS or replaces an operating-system network sandbox.

Strict structural acceptance does not establish truth, evidence verification, business
validity or authorization. A valid proposal cannot update domain records or dispatch
tools. Timeouts stop client waiting but may not immediately cancel server computation.
Requested generation options are not proof of all effective server/model defaults,
memory use or reproducible model outputs.

## Evidence and revisiting triggers

The [design](../phase-5/design.md) defines deterministic boundary tests and a separate
genuine local smoke. The [acceptance record](../phase-5/acceptance-review.md) must report
actual checks, both supported Python versions, PostgreSQL/migration regressions,
unchanged CareerLab hashes and known limits before a focused commit. Do not treat a
model smoke as extraction accuracy or independent held-out evaluation.

Revisit before a new model/server version, additional provider, semantic Career
capability, raw-text input, real personal data, model-run persistence, tool/effect
authority, background scheduling or AI HTTP use case. Preserve accepted provenance,
synthetic isolation, truth and authorization boundaries in every extension.
