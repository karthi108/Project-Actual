# Evidence-backed application preparation

Status: IMPLEMENTED, canonical acceptance PENDING. Separate provisional checkpoint on `office/continuous-build`. See the [design](design.md) and [office validation debt](../office-build/canonical-validation-pending.md).

The Preparation screen selects current claim references into a CV, compares human-selected exact posting quotations and prepares controlled CV adaptation, application-message or cover-letter units. It displays source text/references before exact content review. Submission and application-status recording remain separate manual actions.

API: `POST /api/v1/cvs`, `/cvs/compare`, `/drafts`; `GET /drafts/{draft_id}`; `POST /drafts/{draft_id}/revise`, `/review`. Commands require current aggregate generation. Revision/review also require exact draft revision and content digest. Actor, time, scope and factual text are server derived. [OpenAPI](openapi-v1.json) generates frontend types; Phase-7 OpenAPI remains frozen.

No free-text assertion or arbitrary paraphrase is certified. Unverified claims are shown separately and excluded from factual units. Synthetic review does not independently verify a real candidate. Selection coverage is a transparent count of supported selected units, without overall score or hiring recommendation; ties remain ties.

Personal-laptop checks:

```powershell
uv sync --locked
./scripts/verify_phase7.ps1
uv run --locked python scripts/verify_frozen_artifacts.py
cd apps/web
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
pnpm format
pnpm build
# With a fresh isolated synthetic API/PostgreSQL at 8765:
pnpm e2e
```

The existing full-suite harness includes Phase-9 tests. PostgreSQL tests require an explicit disposable database; no silently skipped gate. Office results are recorded after actual checks, never inferred from this command list.
