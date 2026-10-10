# Phase 26 — Minimal synthetic teams

Status: IMPLEMENTED synthetic session, organization/workspace, role and shared workflow/review architecture. Office regression checks are provisional; canonical acceptance, real login and tenant deployment remain PENDING.

The problem is sharing work while keeping authority server-derived. `actual.workflows.teams` composes the existing validated IR, persisted runtime, fake connectors, activation and exact approval. It adds no HTTP route, frontend login, external account, employee scoring or real-data intake. See [ADR 0014](../adr/0014-synthetic-team-authority.md).

`Directory.provision/issue/revoke` are trusted operator harness commands, not user/model endpoints. Sessions have a required synthetic token format, masked in memory and stored only as digests with server-selected actor, expiry and revocation. `Teams` verifies a session and current membership for each public operation. Workspace selection never supplies authentication. Organization capabilities default empty; connector references name only the registered fake account/resources.

| Role | Minimum operations |
| --- | --- |
| Viewer | Read workspace-shared runs |
| Operator | Publish/start shared definitions; execute only runs it initiated |
| Reviewer | Exact preview, approve/deny; withdraw its own approval |
| Workspace admin | Workspace membership/reference changes and reviewed step activation; operator/reviewer operations |
| Organization administrator | Organization policy changes, additionally requiring workspace admin membership |

Membership and organization policy changes use revisions and append audit. Publishing cannot overwrite a workflow version. Shared approval pins the operator as execution principal and records the reviewer as approver. A current reviewer membership, current operator session/permission, exact policy version, connector reference, activation and sealed approval are checked immediately before fake dispatch. An admin may also review its own run; enforced dual control is not implemented.

Workflow migration 3 adds a nullable relational initiator. Migration from 1/2 preserves existing payloads, and the earlier dead-letter migration remains additive. Old unassigned runs remain available through the original trusted local store but are excluded from team operations. Accepted Career migration/head is unchanged. New trigger deduplication is also principal-bound. Team metadata uses an explicit separate migration; the operator deployment command and role grants include it. No startup migration occurs.

The deterministic harness covers two fabricated organizations, unknown/expired/revoked sessions, cross-workspace/object denial, role escalation, separate approval/activation audit actors, principal tampering, legacy migration, and revocation after intent reservation. No corporate identity system or provider is accessed. Test tokens are deliberately fake public development inputs, never private credentials or independent held-out data.

Important limits: workspace-wide sharing; one enabled principal per step; operator-bootstrap session management; no SSO, CSRF/browser session flow, SCIM, team UI or remote service. Owner filters protect the application boundary; the shared DB role cannot enforce tenancy against arbitrary SQL compromise. Synthetic labels cannot identify personal content. Real team use requires authenticated transport, storage/privacy/retention, membership/session lifecycle and stronger isolation gates.
