# ADR 0015 — Enterprise identity and isolation require new verified boundaries

Date: 2026-10-07. Status: provisional research decision; real integration and canonical acceptance pending.

## Problem and invariants

Phase 26 demonstrates shared synthetic work with operator-issued sessions. Enterprise use would introduce real identities, administrators, accounts and personal data. Requested organization/workspace IDs, email domains, model output and connector responses must never grant authority. The accepted loopback Career API has no production authentication; forwarding it through an identity proxy would not establish an authenticated tenant contract.

## Decision

Keep the synthetic directory as a test harness. A future enterprise transport must use a reviewed OIDC implementation, resolve a verified issuer/subject to a server-controlled principal, and then resolve current organization/workspace membership. Do not implement token cryptography or a fake SSO endpoint here. Select Authorization Code with PKCE, fixed registered redirects, state/nonce binding, configured issuers/algorithms and bounded key retrieval. Verify signatures, issuer, audience and expiry before issuing a protected application session; never use email as the stable authorization key. These are proposed ACTUAL requirements based on [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation) and [OAuth security BCP](https://www.rfc-editor.org/rfc/rfc9700). Provider selection, key rotation, browser CSRF/cookies, logout, account linking and adversarial integration remain pending.

SCIM is a separate authenticated provisioning boundary. Proposed organization-bound service credentials may create/update/deactivate directory records through explicit policy mappings, revision checks and append audit. Group names cannot automatically become administrators. Deactivation must revoke sessions and prevent new dispatch; already committed dispatch requires reconciliation. Duplicate and out-of-order updates must not resurrect authority. Last-administrator removal requires controlled recovery. Review resource version/conditional update behavior with a real provider against [SCIM protocol](https://www.rfc-editor.org/rfc/rfc7644). No provisioning endpoint or enterprise identity library is introduced.

Current owner filters protect application operations, not arbitrary SQL executed with the shared runtime credential. Prefer a separately credentialed database per organization for an initial real enterprise pilot, if authorized: explicit routing from verified context, separately scoped backups/secrets, and no cross-organization SQL credential in ordinary workers. This costs more operational work but gives a clearer boundary than a client-selected tenant setting. A shared-database alternative requires schema changes and tested row security on every payload, intent, receipt, directory and audit table. PostgreSQL table owners and privileged roles can bypass row security; `FORCE ROW LEVEL SECURITY` and non-owner/non-BYPASSRLS roles require deliberate review. [PostgreSQL 18 row security](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)

Do not retrofit RLS incompletely or alter accepted Career migrations in this research phase. Both deployment choices remain unimplemented. Evaluate actual tenant count, cost, migrations, backup isolation and access patterns before selecting production hosting. Test cross-tenant queries, forgotten filters, pooled connection reuse, exports, uniqueness side channels and administrator access against the selected design.

## Governance and secrets

Enterprise connector accounts and workload identities must be server provisioned and scoped to an organization, exact resource and capability. Models receive typed data, never credentials or arbitrary destinations. Prefer short-lived workload credentials supplied by a reviewed platform; encrypted provider refresh tokens and rotation/revocation require a dedicated secret store and ownership model. Compose file mounts are only private rehearsal inputs, not that secret store.

Organization policy changes need an auditable revision, reviewer and effective-time/revocation rule. A future mandatory separation-of-duties policy must prevent self-approval and survive administrator/approver changes. Current synthetic admins can review their own actions. Emergency authority removal stops new dispatch; it cannot unsend an action after the committed dispatch marker. No new allow-on-error fallback or NEXUS authority source is added.

## Evidence and trade-offs

The existing team harness tests current membership, expiry, scoped resources and shared exact approval. It does not establish OIDC/SCIM, public session transport, tenant isolation against SQL compromise, encryption, regulatory compliance or independent security review. [Phase 27 readiness](../phase-27/README.md) records the next evidence required. Keeping those boundaries explicit avoids installing identity, secrets and cloud dependencies without an actual integration to validate.
