# Phase 8 — Career workflow interface

Status: provisional implementation; canonical acceptance PENDING. This phase uses the existing synthetic FastAPI use cases to inspect jobs/profile support, add fabricated jobs/claims/sources, perform separate exact source/claim reviews, withdraw sources, start preparation and record application status. Navigation is Overview, Jobs, Profile, Skills, Applications and Settings. Status transitions remain the accepted backend contract; unsupported proposed product labels are not invented as persisted states.

React presents state and sends typed intents. It does not implement support qualification, review authority, status transitions or persistence. TypeScript contracts are generated from the Phase-7 OpenAPI artifact; regenerate when the API changes. Conflicts and optimistic declarations remain visible. Source references are displayed as text, never followed. No extraction prompt, model configuration, evaluator artifact, migration or Python runtime dependency changes.

The Next server binds loopback port 3000. A narrow bridge validates UI Host, exact same origin/fetch context, methods, paths, query fields and bounded command bytes before forwarding to the fixed loopback API at 8765. It forwards no cookies, authorization or caller-supplied authority headers. FastAPI retains its own accepted loopback/Host/origin/closed-JSON checks. The bridge translates the origin only after validation; it is not a general proxy. Neither server authenticates local callers, so real data remains prohibited.

Mutation retries are disabled. After a failed/uncertain command, reload successful current state before a new action. The backend retains generation/revision/digest conflict and duplicate-intent enforcement. No external effects, login, account integration or real-data mode is provided. UI caches are memory-only; responses are no-store and source/job prose is escaped React text. CSP currently permits inline framework scripts/styles; stronger nonce policy and canonical security review remain validation debt.

## Commands

Use Node 24 and pnpm 11.19.0. From `apps/web`:

```powershell
pnpm install --frozen-lockfile --ignore-scripts
pnpm run types:generate
pnpm run typecheck
pnpm run test
pnpm run format
pnpm run build
pnpm run dev
```

Configure and launch the synthetic API using [Phase 4](../phase-4/README.md), with a private disposable database already migrated and `ACTUAL_API_PORT=8765`. Open `http://127.0.0.1:3000`. An absent synthetic workspace can be initialized with the fabricated example button. Do not use a real runtime database for development tests.

The real browser journey requires a fresh migrated disposable database and synthetic API at 8765. `scripts/phase8_browser_api.py` is a test-only helper: it requires `ACTUAL_TEST_DATABASE_URL` and explicit `ACTUAL_BROWSER_TEST_DISPOSABLE=phase8-owned-native-cluster`, migrates only the operator-designated disposable database and uses a fixed fabricated workspace. It must never target runtime storage. Start it from the repository root using `python scripts/phase8_browser_api.py`; build the frontend, then from `apps/web` run `pnpm run e2e`. Playwright starts/stops its own Next server and uses a fresh headless Edge context. No browser download or existing user profile is required on this office machine. For canonical environments without Edge, review the Playwright channel configuration and install supported test browsers under the personal environment's policy.

## Dependencies and trade-offs

Node 24.19.0 meets [Next's Node 20.9+ contract](https://nextjs.org/docs/app/getting-started/installation) and [Vitest's supported Node branches](https://vitest.dev/guide/). Exact dependency pins and resolved integrity hashes are in package.json/pnpm-lock.yaml. Registry release timestamps were checked on 2026-10-06. Direct/transitive resolution uses a strict seven-day release age and lifecycle scripts disabled. An initial resolution contained fresh releases and package-manager-generated exclusions; it was discarded and rebuilt using mature pins without exclusions.

Next 16.3.7, React 19.3.0, TypeScript 5.9.3, Tailwind 4.3.3, TanStack Query 5.104.0/Table 8.21.3, Vitest 5.0.2/Vite 8.3.1 and Playwright 1.63.0 are pinned. TypeScript 5 satisfies openapi-typescript 7.13.0's peer constraint; the current TypeScript 7 release does not. Table v8 provides the table API used here; no React Compiler is enabled. Peer resolution, strict typing and actual runtime checks validate this combination. The shadcn-style Button/Card are small owned adaptations of the [MIT component recipes](https://ui.shadcn.com/docs/installation/manual), with Radix Slot/CVA utilities and components.json; no opaque UI package or remote registry runtime is required. React Flow has no graph to visualize and is not added.

The same-origin bridge adds a small transport boundary but avoids weakening the accepted API's origin rules. Browser checks here are office evidence only. See [validation debt](../office-build/canonical-validation-pending.md) for actual results and personal acceptance requirements.
