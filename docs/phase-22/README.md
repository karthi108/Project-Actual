# ACTUAL-side NEXUS authorization adapter

IMPLEMENTED proposed contract and fake protocol harness. Real interoperability: PENDING_CANONICAL_INTEGRATION. No NEXUS repository/service is configured or contacted here.

`Authorizer` is ACTUAL's authorization port. `LocalPolicyAuthorizer` keeps ACTUAL usable independently. `NexusAuthorizer` implements a proposed bounded request/decision protocol for synthetic loopback harnesses only. It binds server owner/principal, capability/resource, workflow/step, canonical arguments, optional business intent and policy version. A request ID plus full request digest pins the response. Decisions have an ID and short expiry, and are re-requested at each current authorization check rather than cached across dispatch.

Proposed endpoint: `POST /v1/authorize`, JSON `actual-nexus-v1`. A 200 closed decision must echo request ID/digest, match policy version and expire within 30 seconds. Unknown/extra fields, missing context, redirects, non-JSON/compressed/oversized responses, stale/mismatched decisions, 429/500 and timeout deny. Diagnostics/body text are never exposed. The harness fixes the destination to loopback and disables environment proxy and redirects; workflows cannot choose a host or URL.

MockTransport tests exercise exact semantics without starting or claiming a NEXUS server. The decision metadata is available for trusted audit correlation, not permission inferred from model text. Production protocol compatibility, service identity/TLS, credential/workload identity, policy version semantics, decision audit persistence and revocation timing require real NEXUS review. The current adapter cannot activate a real remote service or credentialed provider.
