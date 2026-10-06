# Phase 7: verification on the current laptop

Date: 2026-10-06, Europe/Paris. Status: **IMPLEMENTED / OFFICE VERIFIED / CANONICAL ACCEPTANCE PENDING**. Accepted base and initial HEAD were `bdc988a` on `main`. The working tree already contained Phase-7 implementation, tests and an acceptance draft. The user explicitly authorized preserving, reviewing and finishing that work. The later continuous-build request authorizes a Phase-7 WIP checkpoint and automatic development through Phase 27 on office/continuous-build; no acceptance tags. Private-remote pushes are conditional on an existing configured remote and permitted credentials.

The continuation reviewed the Phase-0 contracts, accepted milestone documentation, Phase-7 design, profile/domain changes, service intents, matching projection, HTTP surface, tests and replay boundaries. No additional application-code change was needed. The final verification described here is separate from the inherited timings in the original Phase-7 acceptance record.

## Fresh environment and executed checks

The copied `.venv` referenced unavailable `C:\Python313` and was preserved under ignored `local-data/migration-tools/copied-old-venv`. Fresh environments use Python **3.13.13** and **3.14.4**, both within the accepted supported branches. Portable **uv 0.11.7** installed the unchanged lockfile into each environment. No dependency pin, lockfile or accepted migration changed.

Docker and the documented default interpreter paths were absent. The repository's accepted manual disposable-PostgreSQL workflow was used with fresh native **PostgreSQL 18.6** from [EDB's official Windows archive](https://sbp.enterprisedb.com/getfile.jsp?fileid=1260609). An ignored local harness initialized a unique temporary cluster outside the source checkout with SCRAM authentication, a generated private password and an ephemeral `127.0.0.1` port. Every database test used its accepted isolated-schema fixtures and committed Alembic migration. The harness stopped and removed the owned cluster, restored the previous test environment and left no credential file. The default Docker-based `verify_phase7.ps1` was not rerun on this laptop.

| Check actually run | Reproduced result |
| --- | --- |
| Complete suite, Python 3.13.13, real PostgreSQL | **1,456 passed**, no skips; pytest reported 190.37 seconds |
| Complete suite, Python 3.14.4, real PostgreSQL | **1,456 passed**, no skips; pytest reported 189.67 seconds |
| Migration, drift, guards, rollback, concurrency and HTTP integration | Passed in both complete suites; head remains `0001_career_persistence` |
| Ruff source/test/migration lint and formatting | Passed; 123 files already formatted |
| Accepted inference/evaluation helpers plus new replay helper lint/format | Passed |
| Strict mypy, Python 3.13 and 3.14 targets | Passed; 80 source files; 3.14 target also checked using the 3.14 interpreter |
| CareerLab integrity, both interpreters | Passed; eight public cases, unchanged record identities; future splits unmaterialized |
| Retained-source replay, both interpreters | PASS; 87 selections, unchanged input snapshots and exact projection checks; all nine evaluation dictionaries match the accepted report |
| Stored Phase-7 replay and OpenAPI | Reproduced exactly; replay reports agree across interpreters |
| Accepted-base preservation | 199 tracked files outside the 11 authorized edits unchanged, including seven historical manifests, frozen evidence, observable fixtures, lockfile and migrations |
| Whitespace | `git diff --check` passed |

## Exact local model restoration and smoke

Portable **Ollama 0.34.3** was downloaded from its [official release](https://github.com/ollama/ollama/releases/tag/v0.34.3) and checked against the published Windows archive SHA-256. The missing documented **qwen3:4b-instruct** model was restored into ignored local storage and its complete catalog digest matched the accepted `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`.

The unchanged `scripts/verify_phase5_live.py` passed on both interpreters. Each run verified its owned loopback listener and cloud-disabled status, sent only the fixed synthetic color probe, recorded five TCP observation samples with no detected non-loopback established peer, and stopped its owned server. Requested settings remained context 4096, output 128, temperature 0, seed 42 and deadline 120 seconds. Gateway durations were approximately 19.40 seconds on 3.13 and 14.87 seconds on 3.14. These are connectivity checks, not an extraction benchmark, performance comparison or fresh fit-accuracy claim. TCP sampling has the accepted transient-traffic and UDP/DNS limitations.

Model restoration was a separate download operation before the smoke checks. The smoke helpers downloaded zero models and wrote zero application state. Neither prompts/results, credentials, weights nor private test configuration enter Git.

## Windows launch handling and reproducible entry points

This host returned access-denied errors for uv-generated Python and console launchers, including outside the sandbox. Recreating the virtual-environment Python launcher with the installed interpreter's standard `venv` module made Python launchable. Generated tool/application console launchers remain unavailable. Their root cause was not established; no security policy was disabled or weakened. Equivalent Python module commands were executed successfully:

```powershell
& '.\.venv\Scripts\python.exe' -m actual.careerlab verify --manifest datasets/manifests/careerlab-profile-env-v1.json
& '.\.venv\Scripts\python.exe' -m mypy --python-version 3.13
& '.\local-data\migration-tools\venv314\Scripts\python.exe' -m mypy --python-version 3.14
& '.\.venv\Scripts\python.exe' scripts/verify_phase7_profile.py
```

For a privately configured **disposable** PostgreSQL database, the verified full-suite form is:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q --tb=short --basetemp=.pytest-tmp-careerlab-migration-313
& '.\local-data\migration-tools\venv314\Scripts\python.exe' -m pytest -q --tb=short --basetemp=.pytest-tmp-careerlab-migration-314
```

The database URL remains a private process environment variable; never substitute a runtime database. The local `local-data/migration-tools/verify_native_postgres.ps1` harness is ignored machine-specific setup, not new ACTUAL infrastructure. Initial PostgreSQL startup attempts inside the sandbox failed its required Windows restricted-token creation. Outside the sandbox, PowerShell's process-tree wait caused the controller to hang; waiting for `pg_ctl` alone corrected that local harness. Interrupted owned clusters were confirmed stopped and removed before the successful full run.

The existing API/model modules also have their accepted `__main__` entry points. Their existing configuration and real-data restrictions remain binding; this verification did not start a persistent API service. Portable tools are local to this checkout and were not added to global PATH or registered as services.

## Scope and closure

Claim declarations, source review and claim acceptance remain separate. Contextual experience cannot support or refute unscoped generic tenure, periods are never summed, and unknown activity dates remain unknown. Job Intelligence consumes the admitted deterministic projection. Evaluator labels remain outside extraction input. Synthetic review does not independently verify a real person. The unauthenticated synthetic-only restriction, transient assessments/views and all documented profile limitations remain in force.

The Phase-7 WIP checkpoint records these office checks. They do not establish canonical acceptance. Continue to Phase 8 under [ADR 0010](../adr/0010-continuous-office-build.md); personal-laptop regression, runtime, security and live evaluation gates remain pending. [Machine-readable evidence](migration-verification-v1.json) records interpreter, database, smoke and artifact identities.
