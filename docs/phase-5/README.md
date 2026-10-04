# Phase 5: local structured model gateway

ACTUAL can call one local Ollama/Qwen provider through an internal typed gateway.
The only shipped inference capability is a small synthetic connectivity probe.
It accepts color tokens and returns a validated proposal; it does not analyze jobs,
profiles or CVs. See [the design](design.md), [ADR 0006](../adr/0006-local-model-gateway.md)
and [acceptance evidence](acceptance-review.md) for the contract, checks and limitations.

## Local model selection

The inspected Windows installation has Ollama **0.34.3** and these local Qwen models:

| Installed model | Approximate installed size | Phase-5 choice |
| --- | --- | --- |
| `qwen3:4b-instruct` | 2.5 GB | Default: the smallest installed instruction model for this text-only probe |
| `qwen3.5:4b-q4_K_M` | 3.4 GB | Configurable alternative; its vision capability is unused |
| `qwen3:8b` | 5.2 GB | Configurable alternative with a larger memory footprint |

The inspected host has approximately 16 GB RAM and 4 GB GPU memory. Installed weight
size alone does not prove a model will fit entirely on the GPU: context, runtime
buffers and other processes also use memory. The default is a conservative local
development choice, not a measured Career-quality winner. No model download,
installation change or comparison benchmark is part of this phase.

The shared server at `127.0.0.1:11434` reported cloud features enabled during inspection.
ACTUAL refuses to send a probe to that server until its status explicitly reports cloud
disabled. Setting a variable in the ACTUAL client process does not reconfigure an
already-running Ollama server. The supplied live-verification helper starts a separate,
temporary cloud-disabled server without changing the shared installation.

## Run deterministic checks and the separate live check

From the repository, with uv, Docker and Python 3.13/3.14 installed:

```powershell
uv sync --locked
./scripts/verify_phase5.ps1
```

This runs lint, formatting and strict typing, then the complete current regression
suite on both supported interpreters against a disposable PostgreSQL database.
The script reuses the unchanged accepted Phase-3 harness; its historical container
names do not change the tests selected by the current project configuration.
Normal tests use fake providers and injected HTTP transports. They do not invoke Qwen.
Interpreter overrides follow [Persistence usage](../phase-3/README.md).

Run the genuine local inference check separately:

```powershell
$env:ACTUAL_MODEL_MODE = 'synthetic-development'
uv run --locked python scripts/verify_phase5_live.py
```

The Windows helper requires the installed `ollama` executable and existing model
directory. It starts its own hidden `ollama serve` child on an available `127.0.0.1`
port, with `OLLAMA_NO_CLOUD=1`, pruning and request-debug logging disabled, a minimized
child environment and the existing model directory. It verifies cloud-disabled status
and the exact listening child-process identity, invokes the fixed probe and stops its
child in `finally`. During the call it samples established TCP connections for its
server and runner descendants, reports the sample count and fails if a non-loopback
peer is observed. Sampling cannot rule out transient TCP connections, UDP or DNS,
and does not enforce an operating-system firewall. It does not pull
models, stop the shared server, write application state or retain server output.
`OLLAMA_MODELS`, when supplied, selects an existing installed-model directory; the
default is the current Windows user's `.ollama/models` directory.

The helper prints inference metadata and its check outcome. A successful live check
establishes connectivity and validated structured inference through the real provider.
It is not a Job Intelligence evaluation, accuracy score or performance benchmark.
Actual acceptance results belong in [acceptance evidence](acceptance-review.md).

CareerLab generation and verification remain separate from inference:

```powershell
uv run --locked careerlab generate --manifest datasets/manifests/careerlab-model-env-v1.json
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-model-env-v1.json
```

Select this new environment manifest explicitly. The four historical manifests and
all accepted observable/oracle record hashes remain baselines. The accepted CLI default
still selects the Phase-1 manifest. No manifest, evaluator record, future outcome or
held-out input is supplied to a model. Validation and locked-test datasets remain
unmaterialized; the eight public development fixtures share ancestry.

## Use the fixed local diagnostic

For an independently configured local-only Ollama 0.34.3 server:

```powershell
$env:ACTUAL_MODEL_MODE = 'synthetic-development'
$env:ACTUAL_OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:ACTUAL_OLLAMA_MODEL = 'qwen3:4b-instruct'
uv run --locked actual-model-probe
```

The command takes no arguments, files or caller-provided prompts. Its input is always
the explicitly synthetic token tuple `red`, `blue`, `green`. Success prints metadata
to stdout; the structured run log goes to stderr. Failure prints a fixed failure code
and exits nonzero. Neither output includes the prompt or generated result content.
There is no AI HTTP endpoint, interactive chat or tool interface.

| Environment setting | Default / accepted values |
| --- | --- |
| `ACTUAL_MODEL_MODE` | Required: exactly `synthetic-development` |
| `ACTUAL_OLLAMA_BASE_URL` | `http://127.0.0.1:11434`; HTTP, explicit port, host `127.0.0.1`, `localhost` or `::1` only |
| `ACTUAL_OLLAMA_MODEL` | `qwen3:4b-instruct`; one of the three inspected Qwen identifiers above |
| `ACTUAL_MODEL_TIMEOUT_SECONDS` | `120`; whole-number environment value from 1 to 300 |
| `ACTUAL_MODEL_CONTEXT_TOKENS` | `4096`; whole-number value from 512 to 8192 |
| `ACTUAL_MODEL_MAX_OUTPUT_TOKENS` | `128`; whole-number value from 16 to 512 |

`localhost` is canonicalized directly to `127.0.0.1`, without DNS. IPv6 uses
`http://[::1]:PORT`. Credentials, external hosts, URL subpaths, queries and fragments
are rejected. Client proxies and redirects are disabled. Temperature is fixed at zero
and seed at 42; there is no paid-provider/key setting or automatic remote fallback.
Model tags are checked against the local catalog before every inference. The adapter
also requires local GGUF Qwen metadata, completion support and no remote-model fields.

The Ollama server is a separate trusted local process. Its supported local-only
configuration is described in the [official FAQ](https://docs.ollama.com/faq).
ACTUAL verifies reported configuration; this is not an operating-system firewall or
protection against a compromised host/server. The current provider deliberately
rejects server versions other than 0.34.3 pending compatibility review.

## Call the internal abstraction

Capability code uses the gateway and protocol rather than Ollama request dictionaries:

```python
from actual.capabilities.probe import PROBE, ProbeInput, ProbeOutput
from actual.models.contracts import ModelProvider, Proposal
from actual.models.gateway import ModelGateway


async def run_probe(provider: ModelProvider) -> Proposal[ProbeOutput]:
    gateway = ModelGateway(provider, capabilities=(PROBE,))
    return await gateway.run(
        PROBE, ProbeInput(synthetic=True, tokens=("red", "blue"))
    )
```

`proposal.value` is the strictly validated output. `proposal.metadata` identifies the
provider/model, requested options, capability/version, schema hash, prompt hash,
observed model digest/server version and timings. `proposal_only=True` states the
trust boundary. Structural validity cannot certify factual correctness, authorize an
action or verify evidence. The gateway does not check whether the probe's count is
semantically correct; it checks its declared types and bounds.

The configured model retains its installed base tag; `response_model` preserves the
provider's accepted wire echo, which may be that tag or the exact tag plus `:local`.
No other alias is silently accepted.

The shared provider contract permits `model_digest` and `server_version` to be `None`
when a provider cannot obtain them; metadata JSON then contains `null`. The current
Ollama adapter requires and supplies both. Missing information is never replaced by
an invented digest or version.

The shipped probe permits at most eight values from `red`, `green`, `blue`; no raw-text
or CareerLab-to-prompt mapping exists. Trusted developers can define future registered
capabilities, but must establish their privacy, semantic and domain gates in the
appropriate accepted phase. Existing Career commands and domain contracts are unchanged.

## Failures and limits

| Failure code | Meaning |
| --- | --- |
| `configuration` | Unsafe destination, unapproved model, invalid limits or invalid capability configuration |
| `local_privacy_required` | Cloud-disabled/local-model requirements were not established |
| `provider_unavailable` | Connection to the configured local server failed |
| `model_not_found` | Requested installed model is absent or the provider reports it missing |
| `model_unavailable` | Model cannot load/run or lacks completion support |
| `timeout` | The bounded inference operation exceeded its deadline |
| `provider_failure` | Other transport/HTTP/provider failure |
| `invalid_provider_response` | Malformed/incomplete/incompatible provider envelope or wrong model identity |
| `invalid_output` | Generated content is not strict JSON satisfying the output schema |
| `input_rejected` | Caller input is not the exact validated registered input shape |
| `unsupported_capability` | Capability is not registered at this gateway |
| `output_limit` | A provider/schema/result byte limit was exceeded |

There is one attempt: no transport retry, malformed-output retry or repair loop.
The deadline includes provider preflight and response reading, including slow-drip
responses. ACTUAL stops waiting on timeout; cancellation does not guarantee immediate
termination of computation inside Ollama. Requests use `keep_alive=0` to avoid retaining
the loaded model after the operation.

Input JSON is limited to 4096 UTF-8 bytes; instructions to 8192; output schema to
16384; model output to 32768; each provider envelope to 131072. JSON nesting is bounded
and duplicate keys, invalid Unicode and non-finite numbers are rejected. Context/output
token settings are requests to the model server, not a universal tokenizer budget proof.
Metadata records these requested settings; it does not attest every effective server
default, enforce a hardware memory budget or guarantee identical generations.

## Privacy and remaining work

ACTUAL retains raw prompts/results in memory only and adds no model-run table, event,
file archive or debug-content logging option. Run logs contain only correlation ID,
provider/model/capability labels, duration, outcome and fixed error code. Returned
metadata includes the local endpoint and content hashes; treat future metadata as
potentially linkable rather than assuming hashing anonymizes it. Console-capture
retention and the separate Ollama service's logging are operator responsibilities.

No real personal-data path is enabled. The accepted Phase-4 synthetic restriction and
future authentication/deletion prerequisites remain binding. No paid API, tools, CV
tailoring, fit scoring, job extraction, application generation, connector, workflow
execution or Phase-6 behavior is introduced. Model tags/digests and low temperature
do not guarantee immutable loaded weights or identical generations. Read the
[design limitations](design.md#known-limitations) before extending the boundary.
