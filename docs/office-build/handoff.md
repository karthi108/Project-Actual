# Final office-development handoff

Status: ACTUAL Phases 7–27 have been implemented to the extent possible in the office development environment with phase-separated WIP checkpoints. Final canonical validation and acceptance remain PENDING on the personal laptop. Real integrations and deployment are not validated by this handoff.

The accepted baseline remains Phases 0–6A at `bdc988ae7cc00379e6b90f1cf22e6c6de192be61`; the original Phase-6 NO-GO is preserved. Read [the working agreement](../../AGENTS.md), [Phase-0 contract](../phase-0/engineering-contract.md), [authorization](../reference/office-continuous-build.md) and [validation debt](canonical-validation-pending.md) before continuing. Fix a failed canonical phase before accepting its dependent phases. One final green test run cannot accept the whole roadmap.

## Git and transfer

Branch: `office/continuous-build`. Accepted base: `bdc988ae7cc00379e6b90f1cf22e6c6de192be61`. Each row below is a local development checkpoint, without acceptance tags. No remote is configured; no push occurred and no new remote/credential was invented.

| Phase | Implementation checkpoint |
| --- | --- |
| 7 | `e23d24d67f709fbf7e40e0d91a306c3af9d6a997` |
| 8 | `d5671a4e322e9e749523db4b7935cd3e361e78ce` |
| 9 | `8e696258f1c223811f8edcaa332fd64eb319bf9a` |
| 10 | `a6f8900f5ef125c393b6d066d6bb1616cf8872aa` |
| 11 | `e291af9535bd25119eb78d350d6b7e83f69fe7fa` |
| 12 | `b5a7e41b07846761bd36ea1fa76b9120bdb6ff01` |
| 13 | `28ea4a2fc0c385e5b6c4f0e2dacfad98d9a440e3` |
| 14 | `a58faa30d80ec9453d975a4248b32d99ed6427d0` |
| 15 | `3e3d15fdd776587e5b1c2e2a3b4476c0b45203f3` |
| 16 | `8fbf723752a580f51532c19a20ab06ad5937f6db` |
| 17 | `7c80ba599b13fd6b54646de86506d5c39e790268` |
| 18 | `a2a91913537920d90435bd6fafb4a9d188c6910b` |
| 19 | `7ff65782ff0cac6346c2e791db10733a402a838c` |
| 20 | `81c2304f94817ec0be4e65a6a17a706cb675ff26` |
| 21 | `6f35e06e377cd3eba48ca813989afaabfb175911` |
| 22 | `3dae58fbb56d9b84f9f0173de5e221a1048e015e` |
| 23 | `e8a77f7f36a29c99de567ed855ef66c36f3f75a0` |
| 24 | `9aec14929b00b086b108d0ac380e00a4b0f08304` |
| 25 | `e910f9502237c8e5fdfc2fe17c5594724f4807c9` |
| 26 | `b1a88715539e0affe80435e584f1050e9dec9663` |
| 27 | Unique `wip(phase-27):` checkpoint containing this document; resolved in the post-commit inventory |

A tracked document cannot embed the hash of its own commit. After the Phase-27 checkpoint, `scripts/office_git_state.py` records the exact HEAD, all 21 full checkpoint hashes, branch, accepted base, working-tree state and remote names, without remote URLs or private content. The finalized local handoff at `local-data/office-build-handoff.md` includes that post-commit inventory plus this document; it is intentionally ignored, generated after the checkpoint. Regenerate the inventory after any later commit:

```powershell
uv run --locked python scripts/office_git_state.py
git status --short
```

Use an authorized private repository or an operator-approved source-only transfer on the personal laptop; office private tools, databases, model weights, logs, credentials and evaluator directories are excluded from Git. The ignored evaluator bootstrap below reconstructs only the eight frozen public development answers. It does not create a held-out set.

## Phase matrix

Every row has canonical acceptance **PENDING**. Office checks refer to synthetic development and recorded regression evidence. Detailed per-check failures, environment dependencies and security gates are in the debt register.

| Phase | Implemented extent | Office evidence | Known limitation / next gate |
| --- | --- | --- | --- |
| 7 | Deterministic evidence-backed profile and separate source/claim review | Full dual-Python/PostgreSQL, 87 retained selections, Qwen smoke | Synthetic reviews are not independent real-person verification; no generic duration inference |
| 8 | Career web UI through the existing API | 22 units, typing/build, real browser/API/database | Loopback synthetic API; accessibility and canonical browser review pending |
| 9 | Source-linked deterministic materials and exact content review | Full regressions and three browser journeys | No external submission; sparse templates and dependency reconciliation |
| 10 | Typed bounded Workflow IR and fixed capability registry | Graph/schema/authority adversarial cases | Acyclic scalar DAG; no arbitrary generated code |
| 11 | Durable fenced PostgreSQL runtime | Real database lease/wait/restart/state checks | One bounded step per tick; no production scheduler |
| 12 | Closed typed fake connector contracts | Permission/resource/output/error checks | Real providers, OAuth and arbitrary URL intake unavailable |
| 13 | Exact approval and durable fake effect intents | Duplicate/version/race/lost-acknowledgement checks | Unknown outcomes reconcile without resend; real provider semantics pending |
| 14 | Isolated synthetic WorkLab replay | Five expected-status/branch matches, zero provider calls | Public development examples; no live/held-out accuracy or ROI |
| 15 | Persisted synthetic shadow comparison | Database scope/deduplication/readiness cases | Human paths are explicit synthetic observations; no automatic activation |
| 16 | Reviewed principal/step activation | Activation/audit/dispatch checks | Fake capabilities only; no personal-account activation |
| 17 | Visible consent-controlled semantic Teach harness | Start/pause/stop/sensitive exclusion cases and console demo | Native browser extension/device capture pending |
| 18 | Deterministic bounded process discovery | Synthetic variants, transitions, gaps and repeated sequence truth | Elapsed time is not human active time or employee productivity |
| 19 | Synthetic transcript/rule confirmation and fake STT port | Privacy/catalog/provenance checks | Real microphone/STT pending; voice remains a human claim |
| 20 | Evidence-linked improvement hierarchy and comparisons | Proposal/review/measurement checks | No invented savings, policy or automated policy promotion |
| 21 | Structured meeting-action and conservative email-triage families | Registered handler/branch/input/preservation cases | No prose task inference or real mailbox/calendar |
| 22 | ACTUAL-side proposed NEXUS protocol/harness | Closed loopback request/response/timeout denial tests | Actual NEXUS source/protocol/identity unavailable |
| 23 | Bounded read retry/jitter, deadlines and dead letters | Database recovery and accepted model fault doubles | Process-kill campaigns, long outages and real OAuth pending |
| 24 | Stored identity, full approval seal and schema guards | Tamper/drift/stale review adversarial cases | Hash consistency is not administrator-proof security |
| 25 | Private deployment configuration, commands and bounded telemetry | Unit/database role checks; four YAML files parsed | Docker/TLS/Collector/Terraform/OVH/hosted CI runtime pending |
| 26 | Synthetic organizations/sessions/roles and shared exact review | Tenant/expiry/revocation/initiator/migration checks | No SSO/SCIM/teams UI; shared SQL role is not tenant isolation |
| 27 | Enterprise ADRs/runbooks, bounded audit export and evaluator bootstrap | Audit snapshot/bootstrap and final checks below | Research readiness only; identity, scaling, DR and compliance evidence pending |

## Final office checks

Final results are recorded before checkpointing. No skipped PostgreSQL test is counted as a pass.

| Check | Result |
| --- | --- |
| Full Python 3.13.13 suite with real disposable PostgreSQL 18.6 | 1,606 passed, zero skips; pytest reported 304.36 seconds |
| Full Python 3.14.4 suite with real disposable PostgreSQL 18.6 | 1,606 passed, zero skips; pytest reported 284.76 seconds |
| Ruff lint / Python source formatting | Passed; 200 Python files formatted |
| Strict typing | Passed on both version targets: 115 configured source/helper files and two new development helpers |
| Frozen integrity | 46 accepted artifacts and two frozen Phase-7 artifacts preserved |
| CareerLab environment / fresh-clone bootstrap | Eight unchanged public development identities verified; evaluator remains ignored/separate |
| Retained-source/profile replay | 87/87 exact projection, selection and unchanged profile/job checks on both interpreters |
| WorkLab development replay | 5/5 expected-status and branch matches on both interpreters; zero provider calls; AI factual accuracy unmeasured |
| Frontend unit / type / format / production build | 22 tests and all checks passed |
| Edge browser/API/PostgreSQL journeys | Three passed in 24.3 seconds; owned API/web/database resources cleaned up |
| Deployment/CI syntax | Four YAML documents parsed; native tool and hosted validation pending |

The initial full run failed before executing tests because the new database deployment test and accepted API deployment test had the same module basename. Only the newer module was renamed to `test_deployment_database.py`; test bodies and the original API test remain intact. The failed output is preserved in ignored `local-data/migration-tools/phase27-initial-collection-failure.log`. Initial helper import formatting was corrected. A broad formatter invocation also suggested changing an accepted Phase-5 documentation snippet; that file was preserved. CI now checks all Python source directories explicitly, while accepted evaluation artifacts are checked separately. No test or accepted contract was weakened.

Final ignored evidence includes `regression-313.log`, `regression-314.log`, their JUnit XML and `native-postgres-checks.json` under `local-data/migration-tools`, two exclusive Phase-27 replay reports, and Playwright output under ignored frontend artifacts. Owned native database/browser harnesses clean up their own processes/clusters. These office harnesses and installed tool binaries are not prerequisites distributed by Git.

## Environment

Office: Windows PowerShell. uv 0.11.7; Python 3.13.13/3.14.4; native PostgreSQL 18.6; Node 24.19.0; pnpm 11.19.0; Next 16.3.7; React 19.3.0; TypeScript 5.9.3; Vitest 5.0.2; Playwright 1.63.0. Versions/locks are preserved, without an unsolicited dependency upgrade.

Ollama 0.34.3; accepted `qwen3:4b-instruct` catalog digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`. Accepted configuration is retained. Final replay used retained source IDs and no fresh model inference; prior Phase-7 smoke remains prior evidence. Canonical live Qwen trials must produce a new separate report.

Docker, Terraform and actionlint are unavailable here; none was installed merely to document it. Registry tag endpoint review did not resolve image digests. Some generated Python console launchers returned access denied, while `python -m` commands worked. Sandbox PostgreSQL initialization could not create a Windows restricted token; the owned native test harness used permitted execution outside the sandbox. Corporate security policy was not changed. Docker Linux host networking, certificate trust, image/users/permissions and Linux wheels require personal-environment validation.

## Personal-laptop validation commands

Commands below run from the repository root unless a different directory is stated. Use installed Python paths deliberately; substitute the two paths if the personal installation differs. Download/install dependencies and prepare Docker only where permitted. Keep real data and credentials out of commands/logs/Git.

```powershell
$actualPy313 = 'C:\Python313\python.exe'
$actualPy314 = 'C:\Python314\python.exe'
& $actualPy313 --version
& $actualPy314 --version
uv sync --locked --python $actualPy313
uv run --locked python scripts/prepare_evaluator_fixtures.py --materialize
uv run --locked python -m actual.careerlab verify --manifest docs/office-build/careerlab-environment.json
uv run --locked python scripts/verify_frozen_artifacts.py
uv run --locked python scripts/office_git_state.py
```

`--materialize` is an explicit fresh-clone evaluator restore, not routine regeneration. Existing changed answers cause refusal. Select `docs/office-build/careerlab-environment.json` explicitly: historical manifests and the CLI default remain frozen baselines and do not describe current project metadata.

The accepted PostgreSQL harness owns a disposable Docker container, migrates fresh test schemas and runs **all current configured testpaths** on both installed interpreters:

```powershell
./scripts/verify_phase3.ps1 -PythonExecutables @($actualPy313, $actualPy314)
```

This helper retains its accepted pinned PostgreSQL image. Inspect that image's version and also reproduce the office PostgreSQL **18.6** gates in a separately owned disposable loopback database; do not replace the accepted helper/image silently. For explicit module-based commands or an additional 18.6 run, configure `ACTUAL_TEST_DATABASE_URL` privately to that disposable database with a test operator allowed to create/drop owned schemas/roles, then:

```powershell
uv run --isolated --python $actualPy313 --locked python -m pytest -q --tb=short --basetemp=.pytest-tmp-canonical-313
uv run --isolated --python $actualPy314 --locked python -m pytest -q --tb=short --basetemp=.pytest-tmp-canonical-314
uv run --locked python -m ruff check .
uv run --locked python -m ruff format --check src tests migrations scripts
uv run --isolated --python $actualPy313 --locked python -m mypy --python-version 3.13
uv run --isolated --python $actualPy314 --locked python -m mypy --python-version 3.14
uv run --locked python -m mypy scripts/prepare_evaluator_fixtures.py scripts/office_git_state.py
```

The tests require real PostgreSQL rather than skipping when the URL is absent. They create and remove their own isolated schemas/roles. Never point them at runtime/personal storage. The full suite covers accepted Career migration round trips, provisional schema guards and additive legacy workflow migration. Focused checks may diagnose a failed gate but do not replace the full runs:

```powershell
uv run --locked python -m pytest -q tests/persistence/test_migrations.py tests/persistence/test_workflow_reliability.py tests/persistence/test_deployment_database.py tests/persistence/test_teams.py tests/persistence/test_audit_export.py
uv run --locked python -m pytest -q tests/workflows tests/persistence/test_workflow_runtime.py tests/persistence/test_effect_approval.py tests/persistence/test_activation.py tests/persistence/test_shadow_storage.py tests/persistence/test_workflow_security.py
uv run --locked python -m pytest -q tests/models tests/intelligence tests/profile tests/application
uv run --locked python scripts/verify_phase7_profile.py
uv run --locked python scripts/evaluate_worklab.py
```

For a deployed synthetic rehearsal, use the [Phase-25 explicit migration/check commands](../phase-25/README.md#personal-environment-rehearsal). Accepted Career Alembic remains separate from explicit provisional workflow/approval/activation/shadow/team migrations. Startup performs no DDL.

Live model gateway and Phase-6A regression require installed Ollama 0.34.3, the accepted existing local model/digest and permitted owned loopback processes. Set `OLLAMA_MODELS` privately if existing weights are outside the default directory; do not download or replace weights as part of a test. The Windows helpers scrub the child environment and own/stop their temporary server:

```powershell
$env:ACTUAL_MODEL_MODE = 'synthetic-development'
uv run --isolated --python $actualPy313 --locked python scripts/verify_phase5_live.py
uv run --isolated --python $actualPy314 --locked python scripts/verify_phase5_live.py
uv run --locked python scripts/evaluate_phase6a_live.py
```

The final command performs fresh synthetic trials and creates a new ignored `evaluation-runs/phase6a-<run-id>.report.json`. Review it separately; do not overwrite frozen original/hardened reports. The 87 retained-selection replay above is not a new live or independent held-out accuracy result. Validation/locked-test datasets remain unmaterialized.

Frontend preparation and checks, with Node 24.19.0 and pnpm 11.19.0:

```powershell
Set-Location apps/web
pnpm install --frozen-lockfile
pnpm test
pnpm typecheck
pnpm format
pnpm build
Set-Location ../..
```

For Playwright, separately provision an **owned empty disposable** loopback database and privately set `ACTUAL_TEST_DATABASE_URL` in the API shell. Ports 8765/3000 must be unused; do not replace existing services. In that API shell:

```powershell
$env:ACTUAL_BROWSER_TEST_DISPOSABLE = 'phase8-owned-native-cluster'
uv run --locked python scripts/phase8_browser_api.py
```

In another shell at `apps/web`, with installed Microsoft Edge matching the configured Playwright channel:

```powershell
pnpm e2e
```

Playwright owns a production Next server with `reuseExistingServer=false`; the API helper alone explicitly migrates its selected disposable database and uses fixed synthetic identities. Stop the owned API and dispose only the selected test database afterward. Screenshots on failure are ignored; do not run against personal/production data. Additional browsers, accessibility and native extension runtime remain canonical gates.

Deployment syntax and native CI checks:

```powershell
node scripts/check_deployment_config.mjs
actionlint .github/workflows/verify.yml
terraform -chdir=deploy/terraform fmt -check
terraform -chdir=deploy/terraform init -backend=false
terraform -chdir=deploy/terraform validate
```

The Node syntax helper uses the frozen frontend installation; it is not actionlint/Terraform/Docker validation. Install or use these tools only in the permitted personal validation environment when running their gates. Inspect the generated Terraform dependency lock/checksums and protected state plan. Do not `apply` merely to validate syntax. OVH enablement defaults false and needs separately reviewed account/region/image/network/SSH inputs.

On a supported dedicated Linux Docker host, provision the ignored secret files and separate migration/runtime roles as documented in Phase 25, then:

```sh
docker compose -f deploy/compose.yaml config --quiet
docker compose -f deploy/compose.yaml build
docker compose -f deploy/compose.yaml up -d postgres
docker compose -f deploy/compose.yaml --profile operator run --rm migrate
# Provision/review deploy/runtime-role.sql and its separate password before API startup.
docker compose -f deploy/compose.yaml up -d api web
docker compose -f deploy/compose.yaml exec api python -m actual.deployment check
curl --fail http://127.0.0.1:8765/health/ready
docker compose -f deploy/compose.yaml --profile telemetry run --rm collector validate --config=/etc/otelcol/config.yaml
docker compose -f deploy/compose.yaml down
```

Check image availability/digests, Linux wheels, non-root volume ownership, role grants, read-only filesystems, ports/firewalls and Collector span interoperability; syntax passing cannot establish those. Validate the TLS probe with reviewed Nginx/OpenSSL and trusted operator certificates. The probe grants no API access. Hosted GitHub Actions requires an authorized private remote; run both matrix jobs and review actual logs. CI has read-only permissions and no deployment step.

## Integrations still unavailable

Personal Gmail/Calendar/files and OAuth are fake connector contracts only. Real credentials, scope consent, account/resource identity, expiry/revocation, provider limits, stable idempotency and unknown-outcome recovery are unresolved integration work. No email, calendar event or application was sent.

NEXUS is an ACTUAL-side proposed protocol; the actual source/service/agreed protocol is required for interoperability. Native browser extension/capture and voice microphone/local STT require real runtime, visible consent/privacy gates and canonical evidence. OVHcloud, real deployment, domain/TLS, Collector and hosted CI need permitted personal infrastructure/configuration. SSO/SCIM, enterprise secrets, workload identity, stronger tenancy, ingestion capacity, disaster recovery and numerical SLO/SLA remain Phase-27 research gates.

No company/private service or real-data path was activated. Accepted persistence, HTTP restrictions, ModelGateway constraints, exact deterministic profile projection and CareerLab evaluation isolation remain binding across every future integration.
